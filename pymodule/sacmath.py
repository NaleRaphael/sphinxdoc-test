"""
Math library for SAC file.
"""

import numpy
import matplotlib.pylab as plt
import obspy
import scipy.signal
import sacdate


def decimate(trace, fs_new, rm_dc=True, round_time=False):
    """
    Decimate an obspy.Trace data.
    `obspy.Trace.resample()` is implemented by Fourier method, so it cannot 
    work properly when resampling fator (fs_ori / fs_new) is too high.

    Parameters
    ----------
    trace : obspy.Trace
        An obspy.Trace object.
    fs_new : int
        New sampling rate.
    rm_dc : bool
        Remove DC component.
    round_time : bool
        Round timestamp to a specific unit.
    """
    if not isinstance(trace, obspy.Trace):
        raise Exception('Invalid `trace` object.')

    if trace.stats.sampling_rate < fs_new:
        raise Exception('New sampling rate is greater than the original one.')

    ds_rate = int(trace.stats.sampling_rate/fs_new)

    # Remove dc. This operation prevents discontinuity occuring when padding
    # zeros at the endpoints of data.
    if rm_dc:
        trace.data -= numpy.mean(trace.data)

    if round_time:
        dsr_st = sacdate.roundtime(trace.stats['starttime'].datetime)
        dsr_st = obspy.UTCDateTime(dsr_st)
        trace.stats['starttime'] = dsr_st

    trace.data = scipy.signal.decimate(trace.data, ds_rate)
    trace.stats.sampling_rate = fs_new


def spectrogram(data, NFFT=128, Fs=2, noverlap=0, mode='complex',
                axis_datetime=True, header=None, show_fig=False, save_fig=True, 
                dpi=99.9, figsize=(16.67, 8.13), outpath=None, cmax_ratio=1, 
                normalize_spec=True, auto_adjust=False, cmax=-1, **kwargs):
    """
    Compute spectrogram.
    
    Reference
    ---------
    plt._axis.specgram
    http://stackoverflow.com/questions/23139595/dates-in-the-xaxis-for-a-matplotlib-plot-with-imshow
    http://stackoverflow.com/questions/35420052/adding-colorbar-to-a-spectrogram
    """
    if axis_datetime:
        if header == None:
            raise Exception('No given `header`.')
        if not isinstance(header, obspy.core.trace.Stats):
            raise Exception('Given `header` is not a `obspy.core.trace.Stats object`.')

    # compute complex spectrogram
    spec, freqs, t = plt.mlab.specgram(data, NFFT=NFFT, Fs=Fs,
                                       noverlap=noverlap, mode=mode)

    spec /= len(data)
    Z = None
    # get magnitude
    if mode == 'magnitude':
        Z = spec
    else:
        Z = numpy.abs(spec)

    # flip it (for plotting spectrogram)
    Z = numpy.flipud(Z)

    # prepare args for plotting spectrogram
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([0.1, 0.13, 0.7, 0.77]) #[left bottom width height]
    ax_colorbar = fig.add_axes([0.83, 0.13, 0.03, 0.77])
    y_lims = [0, Fs/2.]
    cm = plt.cm.jet

    vmin = numpy.amin(Z)
    vmax = numpy.amax(Z)

    # normalize
    if normalize_spec:
        Z -= vmin
        Z /= (vmax-vmin)
        vmax = 1.0
        vmin = 0.0

    # auto adjust the cmax for a better view of spectrogram
    if cmax == -1:
        if auto_adjust and mode == 'magnitude':
            hist, bin_edges = numpy.histogram(Z.reshape(-1), bins=20)
            idxmax = hist.argmax()
            if idxmax == len(bin_edges)-1:
                idxmax -= 1
            cmax = (bin_edges[idxmax]+bin_edges[idxmax+1])/2
        else:
            cmax = vmax*cmax_ratio

    if cmax <= vmin:
        plt.close()
        plt.clf()
        raise Exception('`cmax_ratio` is too small.')

    extent = None
    if axis_datetime:
        stn = plt.date2num(header['starttime'].datetime)
        etn = plt.date2num(header['endtime'].datetime)
        extent = [stn, etn, y_lims[0], y_lims[1]]
    # plot spectrogram
    ax.imshow(Z, cm, extent=extent, vmin=vmin, vmax=cmax, aspect='auto')

    # plot colorbar
    mappable = ax.images[0]
    plt.colorbar(mappable=mappable, cax=ax_colorbar)

    if axis_datetime:
        # set x axis as datetime
        ax.xaxis_date()
        date_format = plt.DateFormatter('%m/%d')
        ax.xaxis.set_major_formatter(date_format)
        fig.autofmt_xdate()
        ax.set_xlabel('DateTime')
    else:
        ax.set_xlabel('Samples')

    ax.set_ylabel('Frequency (Hz)')
    if outpath:
        from os import path as op
        temp = op.basename(outpath).split('.')
        fbasename = '.'.join(temp[:-1])
        ax.set_title('Spectrogram, {0}'.format(fbasename))
    else:
        ax.set_title('Spectrogram')

    fig = plt.gcf()
    if save_fig:
        fig.savefig(outpath, dpi=dpi)

    if show_fig:
        plt.show()

    plt.close('all')
    plt.cla()
    plt.clf()

    del Z, mappable
    return spec, freqs, t
