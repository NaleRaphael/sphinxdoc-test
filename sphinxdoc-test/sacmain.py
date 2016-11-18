"""
Script for SAC file handling.
"""

import argparse
import glob
import gc
import os
import time
import traceback

import numpy
import obspy
import sacmath
import sacdate

__all__ = ['do_decimate', 'do_merge']

# --- MISSIONS ---
def do_decimate(**kwargs):
    """
    Decimate SAC data.
    """
    # Check whether var is `None`
    var_dict = {'filepath': None, 'outdir': None, 'fs_new': None}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    sac = obspy.read(var_dict['filepath'])
    sacmath.decimate(sac.traces[0], int(var_dict['fs_new']))

    outpath = _auto_serialnum(var_dict['filepath'], var_dict['outdir'])

    # write file
    sac.write(outpath, format='SAC')
    del var_dict, sac
    gc.collect()


def do_decimate_bat(**kwargs):
    """
    Decimate SAC data. (batch)
    
    Parameters
    ----------
    cors : list of string
        Strings for pattern matching.
    rng : list
        Range of solar day for searching.
    """
    var_dict = {'filedir': None, 'outdir': None, 'fs_new': None, 
                'cors': None, 'rng': None}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    # Check `outdir`
    if not os.path.exists(var_dict['outdir']):
        os.makedirs(var_dict['outdir'])

    # TODO: these vars can be parameterized
    fdir = var_dict['filedir']
    gpat = os.path.join(var_dict['filedir'], '*.sac')
    delimiter = '.'
    pats = 's.s.x.s.i'
    cors = var_dict['cors']
    rng = var_dict['rng']
    filelist = _get_filelist(fdir, gpat, delimiter, pats, cors, rng)

    if len(filelist) == 0:
        raise Exception('No SAC file availabe to be decimated.')

    # Open a log file for error recording
    errlogpath = os.path.join(var_dict['outdir'], 
                              '_errlog_{0}.txt'.format(time.strftime('%y%m%d%H%M')))
    errlog = open(errlogpath, 'w')

    sac = None
    for cnt, f in enumerate(filelist):
        print('--- processing: {0}/{1} ---'.format(cnt+1, len(filelist)))
        try:
            sac = obspy.read(f)
            sacmath.decimate(sac.traces[0], int(var_dict['fs_new']))
            outpath = _auto_serialnum(f, var_dict['outdir'])
            sac.write(outpath, format='SAC')
        except Exception as ex:
            # Write into err_list
            errlog.write('{0}: {1}\n'.format(os.path.basename(f), ex.message))
    errlog.close()
    del var_dict, filelist
    gc.collect()


HEADER_DICT = {'nzjday': None, 'nzhour': None, 'nzmin': None, 'nzsec': None, 
               'nzmsec': None}
def do_merge(**kwargs):
    """
    Merge all SAC files under a folder.
    """
    # Check whether var is `None`
    var_dict = {'filedir': None, 'method': None, 'interpolation_samples': None, 
                'fill_value': None, 'round_time': True}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    sacfiles = glob.glob(os.path.join(var_dict['filedir'], '*.sac'))
    if len(sacfiles) == 0:
        raise Exception('No SAC file availabe to be merged.')

    msac = obspy.read(sacfiles[0])
    for f in sacfiles[1:]:
        print('--- adding Trace: {0} ---\r\n'.format(os.path.basename(f)))
        msac += obspy.read(f)

    filled = None
    if var_dict['fill_value'] != 'None':
        filled = int(var_dict['fill_value'])
    try:
        # check that all trace is normal array, not masked array
        for tr in msac:
            if isinstance(tr.data, numpy.ma.masked_array):
                tr.data = tr.data.filled()

        # start merging
        msac.merge(method=int(var_dict['method']),
                   interpolation_samples=int(var_dict['interpolation_samples']),
                   fill_value=filled)

        # roundtime. immutable object.
        if var_dict['round_time']:
            dsr_st = sacdate.roundtime(msac.traces[0].stats['starttime'].datetime)
            dsr_st = obspy.UTCDateTime(dsr_st)
            msac.traces[0].stats['starttime'] = dsr_st

        # modify header
        st = msac.traces[0].stats['starttime'].datetime
        dsr_st = sacdate.roundtime(st, roundtype='month')
        sac_header = msac.traces[0].stats.sac
        sac_header['nzyear'] = st.year
        sac_header['nzjday'] = sacdate.cal_solarday(dsr_st.day, dsr_st.month, dsr_st.year)
        sac_header['nzhour'] = st.hour
        sac_header['nzmin'] = st.minute
        sac_header['nzsec'] = st.second
        sac_header['nzmsec'] = 0
    except:
        raise

    outpath = os.path.join(var_dict['filedir'], 
                           'merged_{0}.sac'.format(time.strftime('%y%m%d%H%M')))
    msac.write(outpath, format='SAC')
    del var_dict, sacfiles, msac, sac_header
    gc.collect()


# TEMP: supported parameters
AVAILABLE_METHOD = ['month', 'year']
EXTRA_INFO_FMT = ['solarday', 'month', 'year']
def do_merge_bat(**kwargs):
    """
    Merge all SAC files under a folder. (batch)
    """
    # duration: duration for one merged file -> currently available: 'month'
    var_dict = {'filedir': None, 'method': None, 'interpolation_samples': None, 
                'fill_value': None, 'outdir': None, 'duration': None, 
                'cors': None, 'extra_info_fmt': None, 'round_time': True}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invalid `{0}`.'.format(k))

    # check extra info format (which is used to indicate the datetime range of 
    # the merged file)
    if var_dict['extra_info_fmt'] and var_dict['extra_info_fmt'] not in EXTRA_INFO_FMT:
        raise Exception('Invalid `extra_info_fmt`.')
    elif var_dict['extra_info_fmt'] is None:
        var_dict['extra_info_fmt'] = 'solarday'   # default

    # TEMP: check whether `duration` is available
    if var_dict['duration'] not in AVAILABLE_METHOD:
        raise Exception('Invalid `duration`: {0}'.format(var_dict['duration']))

    # Check `outdir`
    if not os.path.exists(var_dict['outdir']):
        os.makedirs(var_dict['outdir'])

    rm_tmp = kwargs.get('rm_tmp')

    # Open a log file for error recording
    errlogpath = os.path.join(var_dict['outdir'], 
                              '_errlog_{0}.txt'.format(time.strftime('%y%m%d%H%M')))
    errlog = open(errlogpath, 'w')

    # parse parameters of `obspy.merge()`
    filled = None
    if var_dict['fill_value'] != 'None':
        filled = int(var_dict['fill_value'])
    interpolation_samples=int(var_dict['interpolation_samples'])
    method=int(var_dict['method'])

    # TODO: these vars can be parameterized
    gpat = os.path.join(var_dict['filedir'], '*.sac')
    delimiter = '.'
    pats = 's.x.x.s.i'
    cors = var_dict['cors']
    ref_year = cors[-1]
    for year in ref_year:   # this format is valid only for specific stations
        if len(year.split('_')) != 2:
            raise Exception('Please check `ref_year` (in `cors`)')

    rawlist = glob.glob(gpat)
    month_list = range(1, 13)
    #year = int(cors[-1][0].split('_')[-1])     # TODO: rewrite this

    st_count = 0
    # TEMP: No better solution...
    for stations in cors[0]:
        MERGE_METHOD_ENTRY[var_dict['duration']](
            rawlist, delimiter, pats, stations, ref_year, month_list,
            method, interpolation_samples, filled, var_dict['round_time'], 
            len(cors[0]), st_count, var_dict['extra_info_fmt'], 
            var_dict['outdir'], errlog, rm_tmp=rm_tmp)
        st_count += 1
    errlog.close()
    del var_dict, rawlist


def _merge_into_month(rawlist, delimiter, pats, stations, ref_year, month_list, 
                      method, interpolation_samples, filled, do_round_time, 
                      st_amount, st_count, extra_info_fmt, outdir, errlog, **kwargs):
    total = 12*st_amount
    for y_info in ref_year:
        year = int(y_info.split('_')[-1])
        for m in month_list:
            print('--- merging: {0}/{1} ---'.format(st_count*12+m, total))
            # get sac files corresponding specific range
            rng = sacdate.cal_solarday_rng_of_a_month(m, year)
            # notice that elements in `cors` should be a list
            filelist = _filt_filelist(rawlist, delimiter, pats, 
                                      cors=[[stations], [y_info]], rng=rng)

            if len(filelist) == 0:
                print('!!! no file availabe in given time range.')
                continue

            # read sac files
            msac = obspy.read(filelist[0])
            for f in filelist[1:]:
                msac += obspy.read(f)

            try:
                # check that all trace is normal array, not masked array
                for tr in msac:
                    if isinstance(tr.data, numpy.ma.masked_array):
                        tr.data = tr.data.filled()

                # start merging
                msac.merge(method=method,
                           interpolation_samples=interpolation_samples,
                           fill_value=filled)

                # desired start time and end time
                dsr_st = obspy.UTCDateTime('{0}-{1}-{2}T00:00:00'.format(year, m, 1))
                dsr_et = dsr_st + sacdate.get_day_of_a_month(m, year)*86400

                # trimming / padding
                msac.trim(starttime=dsr_st, endtime=dsr_et, pad=True, fill_value=filled)

                # round time
                if do_round_time:
                    rnd_st = sacdate.roundtime(msac.traces[0].stats['starttime'].datetime)
                    rnd_st = obspy.UTCDateTime(rnd_st)
                    msac.traces[0].stats['starttime'] = rnd_st

                # modify header
                st = None
                if do_round_time:
                    st = rnd_st.datetime
                else:
                    st = dsr_st.datetime
                sac_header = msac.traces[0].stats.sac
                sac_header['nzyear'] = year
                sac_header['nzjday'] = rng[0]
                sac_header['nzhour'] = st.hour
                sac_header['nzmin'] = st.minute
                sac_header['nzsec'] = st.second
                sac_header['nzmsec'] = 0

                # Add extra info (in filename)
                fname_temp = os.path.basename(filelist[0]).split('.')
                fname = '.'.join(fname_temp[:-2])
                fext = fname_temp[-1]
                if extra_info_fmt == 'solarday':
                    outpath = os.path.join(outdir, 
                                           'm_{0}.{1}-{2}.{3}'.format(fname, rng[0], rng[1], fext))
                elif extra_info_fmt == 'month':
                    outpath = os.path.join(outdir, 
                                           'm_{0}.{1}.{2}'.format(fname, str(m).zfill(2), fext))

                # write SAC
                msac.write(outpath, format='SAC')
            except Exception as ex:
                print(ex.message)
                errlog.write('{0}: {1}\n'.format(os.path.basename(f), ex.message))
            del filelist, sac_header


def _merge_into_year(rawlist, delimiter, pats, stations, ref_year, month_list,
                     method, interpolation_samples, filled, do_round_time, 
                     st_amount, st_count, extra_info_fmt, outdir, errlog, **kwargs):
    for y_info in ref_year:
        year = int(y_info.split('_')[-1])
        print('--- merging: {0}/{1} ---'.format(st_count, st_amount))
        # get sac files corresponding specific range
        rng = sacdate.cal_solarday_rng_of_a_year(year)
        # notice that elements in `cors` should be a list
        filelist = _filt_filelist(rawlist, delimiter, pats, 
                                  cors=[[stations], [y_info]], rng=rng)

        if len(filelist) == 0:
            print('!!! no file availabe in given time range.')
            continue

        # read sac files
        msac = obspy.read(filelist[0])
        for f in filelist[1:]:
            msac += obspy.read(f)

        try:
            # check that all trace is normal array, not masked array
            for tr in msac:
                if isinstance(tr.data, numpy.ma.masked_array):
                    tr.data = tr.data.filled()

            # start merging
            msac.merge(method=method,
                       interpolation_samples=interpolation_samples,
                       fill_value=filled)

            # desired start time and end time
            dsr_st = sacdate.roundtime(msac.traces[0].stats['starttime'].datetime)
            dsr_et = sacdate.roundtime(msac.traces[0].stats['endtime'].datetime)

            # re-check range of solar day
            dsr_sd_st = sacdate.cal_solarday(dsr_st.day, 
                                             dsr_st.month,
                                             dsr_st.year)
            dsr_sd_et = sacdate.cal_solarday(dsr_et.day, 
                                             dsr_et.month,
                                             dsr_et.year)
            if dsr_sd_et == 1:  # ex: 2014/01/01 00:00:00
                # actully, we need to calculate the solar day of 
                # 2013/12/31 11:59:59
                dsr_sd_et = sacdate.cal_solarday_rng_of_a_year(dsr_et.year-1)[-1]
            
            # datetime for trimming should be UTCDateTime
            dsr_st = obspy.UTCDateTime(dsr_st)
            dsr_et = obspy.UTCDateTime(dsr_et)

            # trimming / padding
            msac.trim(starttime=dsr_st, endtime=dsr_et, pad=True, fill_value=filled)

            # round time
            if do_round_time:
                rnd_st = sacdate.roundtime(msac.traces[0].stats['starttime'].datetime)
                rnd_st = obspy.UTCDateTime(rnd_st)
                msac.traces[0].stats['starttime'] = rnd_st

            # modify header
            st = None
            if do_round_time:
                st = rnd_st.datetime
            else:
                st = dsr_st.datetime
            sac_header = msac.traces[0].stats.sac
            sac_header['nzyear'] = year
            sac_header['nzjday'] = dsr_sd_st
            sac_header['nzhour'] = st.hour
            sac_header['nzmin'] = st.minute
            sac_header['nzsec'] = st.second
            sac_header['nzmsec'] = 0

            # Add extra info (in filename)
            fname_temp = os.path.basename(filelist[0]).split('.')
            fname = '.'.join(fname_temp[:-2])
            fext = fname_temp[-1]
            if extra_info_fmt == 'solarday':
                outpath = os.path.join(outdir, 
                                       'm_{0}.{1}-{2}.{3}'.format(fname, dsr_sd_st, dsr_sd_et, fext))
            elif extra_info_fmt == 'month':
                outpath = os.path.join(outdir, 
                                       'm_{0}.{1}.{2}'.format(fname, str(dsr_et.datetime.month).zfill(2), fext))
            elif extra_info_fmt == 'year':
                outpath = os.path.join(outdir, 
                                       '{0}.{1}.{2}'.format(fname, dsr_sd_st, fext))

            # write SAC
            msac.write(outpath, format='SAC')

            # remove temp file
            if kwargs.get('rm_tmp'):
                for f in filelist:
                    os.remove(f)
        except Exception as ex:
            print(ex.message)
            errlog.write('{0}: {1}\n'.format(os.path.basename(f), ex.message))
        del filelist, sac_header


MERGE_METHOD_ENTRY = {'month': _merge_into_month, 'year': _merge_into_year}

# desired order of keys in heaeder (excluding `sac`)
hdod = ['network', 'station', 'location', 'channel', 'starttime', 'endtime', 
         'sampling_rate', 'delta', 'npts', 'calib', '_format']
# desired order of `sac` in heaeder
hsacod = ['cmpaz', 'nzyear', 'nzjday', ]

def do_view(**kwargs):
    """
    Return header of a .sac file.
    
    Reference
    ---------
    Trace.stats
    """
    filepath = kwargs.get('filepath')
    sacfile = obspy.read(filepath, headonly=True)

    header = ''  # for storing info
    stats = sacfile.traces[0].stats
    #hsac = stats.get('sac')     # key `sac` is an `AttribDict`

    for k in hdod:
        header += '{0}:{1}\n'.format(k, stats[k])

    # TODO: Rewrite this
    #for k_st in stats:
    #    if k_st == 'sac':
    #        continue
    #    header += '{0}:{1}\n'.format(k_st, stats[k_st])
    print header
    return header


def do_spectrogram(export=True, **kwargs):
    """
    Compute spectrogram. (currently supported: STFT)

    Parameters
    ----------
    time_interval : int
        unit: hour
    """
    var_dict = {'filepath': None, 'outpath': None, 'outpath_im':None, 'save_csv': False,
                'time_interval': 1, 'show_fig': False, 'save_fig': True, 
                'cmax_ratio': 0.1, 'normalize_spec': True, 'auto_adjust': False, 'cmax': -1}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    msac = obspy.read(var_dict['filepath'])
    stat = msac.traces[0].stats
    st = stat['starttime'].datetime
    fs = stat['sampling_rate']
    timeunit = var_dict['time_interval']    # 1 hour
    intv_time = int(3600*timeunit*fs)     # points in a hour

    # compute spectrogram
    spec, freqs, t = sacmath.spectrogram(msac.traces[0].data, NFFT=intv_time, 
                                         Fs=fs, noverlap=0, mode='magnitude',
                                         axis_datetime=True, header=stat,
                                         show_fig=var_dict['show_fig'], 
                                         save_fig=var_dict['save_fig'], 
                                         dpi=99.9, figsize=(12, 4),
                                         outpath=var_dict['outpath_im'], 
                                         cmax_ratio=var_dict['cmax_ratio'],
                                         normalize_spec=var_dict['normalize_spec'], 
                                         auto_adjust=var_dict['auto_adjust'],
                                         cmax=var_dict['cmax'])

    # prepare header
    header = {'DataType': 'Spectra', 'Complex': 'TRUE', 'TimeCount': len(t), 
              'FreqCount': spec.shape[0], 
              'TimeInterval': '{0} hr({1} pts)'.format(timeunit, intv_time), 
              'FreqInterval': fs/2.0/spec.shape[0], 'TimeUnit': 'sec', 
              'FreqUnit': 'Hz', 'TimeFormat': 'Regular', 
              'FreqFormat': 'Regular', 'StartDate': st, 'StartFreq': 0, 
              'FreqAxis': 'LinearAxis'}

    # create datetime axis
    import datetime
    t_axis = numpy.array([st+datetime.timedelta(hours=i) for i in xrange(len(t))])

    # export spectrogram
    if var_dict['save_csv']:
        export_csv(var_dict['outpath'], t_axis, spec, header=header)
    del var_dict, msac, stat, spec, freqs, t, t_axis, header
    gc.collect()


def do_spectrogram_bat(export=True, **kwargs):
    """
    Compute spectrogram. (batch)

    Parameters
    ----------
    time_interval : int
        unit: hour
    """
    var_dict = {'filedir': None, 'outdir': None, 'outdir_im':None, 'save_csv': False,
                'time_interval': 1, 'show_fig': False, 'save_fig': True,
                'cmax_ratio': 0.1, 'normalize_spec': True, 'auto_adjust': False, 'cmax': -1}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    # Check `outdir`
    if not os.path.exists(var_dict['outdir']):
        os.makedirs(var_dict['outdir'])

    # Open a log file for error recording
    errlogpath = os.path.join(var_dict['outdir'], 
                              '_errlog_{0}.txt'.format(time.strftime('%y%m%d%H%M')))
    errlog = open(errlogpath, 'w')

    gpat = os.path.join(var_dict['filedir'], '*.sac')
    filelist = glob.glob(gpat)
    
    inargs = {'filepath': None, 'outpath': None, 'outpath_im': None, 
              'save_csv': var_dict['save_csv'],
              'time_interval': var_dict['time_interval'], 
              'show_fig': var_dict['show_fig'], 
              'save_fig': var_dict['save_fig'],
              'cmax_ratio': var_dict['cmax_ratio'],
              'normalize_spec': var_dict['normalize_spec'],
              'auto_adjust': var_dict['auto_adjust'], 
              'cmax': var_dict['cmax']}

    for i, f in enumerate(filelist):
        print('--- processing: {0}/{1} ---'.format(i, len(filelist)))
        try:
            temp = os.path.basename(f).split('.')
            fbasename = '.'.join(temp[:-1])
            csvname = fbasename + '.csv'
            csvpath = os.path.join(var_dict['outdir'], csvname)
            imgname = fbasename + '.png'
            imgpath = os.path.join(var_dict['outdir'], imgname)
            inargs['filepath'] = f
            inargs['outpath'] = _auto_serialnum(csvpath)
            inargs['outpath_im'] = _auto_serialnum(imgpath)

            do_spectrogram(export=export, **inargs)
        except Exception as ex:
            print(ex.message)
            errlog.write('{0}: {1}'.format(os.path.basename(f), ex.message))
    del filelist, inargs
    gc.collect()


def do_spectrogram_simple(**kwargs):
    var_dict = {'filepath': None, 'outdir': None, 'save_fig': False,
                'save_csv': False, 'show_fig': False,'cmax_ratio': 0.1,
                'normalize_spec': False, 'auto_adjust': True, 'cmax': -1}
    for k in var_dict:
        var_dict[k] = kwargs.get(k)
        if var_dict[k] == None:
            raise Exception('Invliad `{0}`.'.format(k))

    if not os.path.exists(var_dict['filepath']):
        raise Exception('File does not exist: {0}'.format(var_dict['filepath']))

    if var_dict['save_fig'] == True or var_dict['save_csv'] == True:
        if not os.path.exists(var_dict['outdir']):
            raise Exception('Folder does not exist: {0}'.format(var_dict['outdir']))

    inargs = {'filepath': None, 'outpath': None, 'outpath_im': None, 
              'save_csv': var_dict['save_csv'],
              'time_interval': 1, 
              'show_fig': var_dict['show_fig'], 
              'save_fig': var_dict['save_fig'],
              'cmax_ratio': var_dict['cmax_ratio'],
              'normalize_spec': False,
              'auto_adjust': var_dict['auto_adjust'],
              'cmax': var_dict['cmax']}
    
    try:
        temp = os.path.basename(var_dict['filepath']).split('.')
        fbasename = '.'.join(temp[:-1])
        csvname = fbasename + '.csv'
        csvpath = os.path.join(var_dict['outdir'], csvname)
        imgname = fbasename + '.png'
        imgpath = os.path.join(var_dict['outdir'], imgname)
        inargs['filepath'] = var_dict['filepath']
        inargs['outpath'] = _auto_serialnum(csvpath)
        inargs['outpath_im'] = _auto_serialnum(imgpath)

        do_spectrogram(export=True, **inargs)
    except:
        raise
    

# --- Other ---
def _auto_serialnum(filepath, new_dir=None):
    """
    Automatically add a serial number behind `filepath` if there is a duplicate.
    """
    outdir = ''
    outpath = ''
    fbasename = os.path.basename(filepath)
    if new_dir:
        outdir = new_dir
        outpath = os.path.join(outdir, fbasename)
    else:
        outdir = os.path.dirname(filepath)
        outpath = filepath

    # prevent overwriting
    temp = fbasename.split('.')
    fname = '.'.join(temp[:-1])
    fext = temp[-1]
    serialnum = 1
    while os.path.exists(outpath):
        outpath = os.path.join(outdir, 
                               '{0}_{1}.{2}'.format(fname, serialnum, fext))
        serialnum += 1

    return outpath


def _get_filelist(filedir, gpat, delimiter, pats, cors=None, rng=None):
    templist = glob.glob(gpat)
    return _filt_filelist(templist, delimiter, pats, cors, rng)


def _filt_filelist(rawlist, delimiter, pats, cors=None, rng=None):
    """
    Parameters
    ----------
    filedir : string
        Directory for searching.
    gpat : string
        Pattern for `glob.glob`.
    delimiter : string
        Delimiters for patterns. (currently only single delimiter is supported)
    pats : string
        Patterns for filtering.
        example: `s.x.x.s.i`
        s: string
        i: integer
        x: ignorable term
        -> ['s', 'x', 'x', 's', 'i']
    cors : list of strings
        example: [['pat_a1', 'pat_a2'], ['pat_b1', 'pat_b2']]
    rng : optional, 1D-list
        Range for filter integer part.
    """
    split_pat = pats.split(delimiter)

    s_idx = []  # index array of strings
    s_set = []
    i_idx = 0  # index array of integers
    cnt = 0     # TODO: rewrite this into list
    for i in range(len(split_pat)):
        if split_pat[i] == 's':
            s_idx.append(i)
            s_set.append(set(cors[cnt]))
            cnt += 1
            continue
        if split_pat[i] == 'i':
            i_idx = i

    filelist = []
    fbn = None
    temp = None
    for i, f in enumerate(rawlist):
        fbn = os.path.basename(f)
        temp = fbn.split(delimiter)
        chk_num = True
        for cnt, si in enumerate(s_idx):
            if temp[si] not in s_set[cnt]:
                chk_num = False
                break   # not matched -> break this loop
        if chk_num and rng is not None:
            # TODO: Revise this
            num = int(temp[i_idx])
            if rng[0] > num or rng[1] < num:
                continue
            else:
                filelist.append(f)
    return filelist


# does not work. `obspy.core.trace.Stats` is immutable.
def _modify_header(stats, **kwargs):
    if not isinstance(stats, obspy.core.trace.Stats):
        raise Exception('Given `stats` is not obspy.core.trace.Stats')
    for k in kwargs:
        value = kwargs.get(k)
        if value != None:
            stats[k] = value
    return stats


key_header = ['DataType', 'Complex', 'TimeCount', 'FreqCount', 'TimeInterval', 
              'FreqInterval', 'TimeUnit', 'FreqUnit', 'TimeFormat', 
              'FreqFormat', 'StartDate', 'StartFreq', 'FreqAxis']
def export_csv(filepath, t_axis, data, header=None):
    outfile = None
    try:
        outfile = open(filepath, 'w')
    except:
        raise
    
    # write header
    if header:
        for k in key_header:
            value = header.get(k)
            outfile.write('#{0}, {1}\n'.format(k, value))
        outfile.write('\n')

    # write content
    if len(data.shape)==2 and isinstance(data[0,0], numpy.complex):
        for i, t in enumerate(t_axis):
            real_imag_list = ['{0:.6f},{1:.6f}'.format(x.real, x.imag) for x in data[:,i]]
            content = ','.join(map(str, real_imag_list))
            outfile.write('{0},{1}\n'.format(str(t), content))
            del real_imag_list, content
        gc.collect()
    elif len(data.shape)==2:
        for i, t in enumerate(t_axis):
            content = ','.join(map(str, data[:,i]))
            outfile.write('{0},{1}\n'.format(str(t), content))
            del content
        gc.collect()
    else:
        for i, t in enumerate(t_axis):
            outfile.write('{0},{1:.6f}\n'.format(str(t), data[i]))
    outfile.close()
    

SAC_MISSION = {'decimate': do_decimate, 'merge': do_merge, 'view': do_view, 
               'spectrogram': do_spectrogram_simple}

# TODO: replace this
MISSION_ARGS = {
    'decimate': {'filepath': '', 'outdir': '', 'fs_new': -1},
    'merge': {'filedir': '', 'method': 1, 'interpolation_samples': -1, 
              'fill_value': 0}
}

# --- ENTRY ---
def entry(mission, **kwargs):
    try:
        SAC_MISSION[mission](**kwargs)
    except:
        raise


CHECK_BIG5 = ['filepath', 'outdir', 'filedir']
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Handling SAC files')
    parser.add_argument('-m', dest='mission', metavar='mission', 
                        help='Misson to be executed. Available: `decimate`, `merge`, `view`')
    parser.add_argument('--filepath', dest='filepath', metavar='filepath', 
                        help='Path of SAC file')
    parser.add_argument('--outdir', dest='outdir', metavar='outdir', 
                        help='Directory for storing output files')
    parser.add_argument('--fs_new', dest='fs_new', metavar='fs_new', type=int, 
                        help='New sampling rate. (Currently, only decimation is supported)')
    parser.add_argument('--filedir', dest='filedir', metavar='filedir',
                        help='Directory of input files.')
    parser.add_argument('--method', dest='method', metavar='method',
                        help='An arg for `obspy.Stream.merge()`.')
    parser.add_argument('--interpolation_samples', dest='interpolation_samples', 
                        metavar='interpolation_samples',
                        help='An arg for `obspy.Stream.merge()`.')
    parser.add_argument('--fill_value', dest='fill_value', metavar='fill_value',
                        help='An arg for `obspy.Stream.merge()`.')
    parser.add_argument('--round_time', dest='round_time', metavar='round_time',
                        help='Round time. (default unit: month)')
    parser.add_argument('--save_csv', dest='save_csv', 
                        metavar='save_csv', type=int, 
                        help='Save values of spectrogram into a csv file.')
    parser.add_argument('--save_fig', dest='save_fig', 
                        metavar='save_fig', type=int, 
                        help='Save spectrogram into a png file.')
    parser.add_argument('--show_fig', dest='show_fig', 
                        metavar='show_fig', type=int, 
                        help='Show spectrogram in a new window.')
    parser.add_argument('--cmax_ratio', dest='cmax_ratio', 
                        metavar='cmax_ratio', type=float, 
                        help='Ratio of cmax for spectrogram.')
    parser.add_argument('--normalize_spec', dest='normalize_spec', 
                        metavar='normalize_spec', type=int, 
                        help='Normalize spectrogram.')
    parser.add_argument('--auto_adjust', dest='auto_adjust', 
                        metavar='auto_adjust', type=int, 
                        help='Automatically adjust cmax of spectrogram.')
    parser.add_argument('--cmax', dest='cmax', 
                        metavar='cmax', type=int, 
                        help='Cmax of spectrogram.')
    try:
        args = parser.parse_args()
    except Exception as ex:
        print(ex.message)

    # TODO: Rewrite this operation
    arg_dict = vars(args)
    try:
        if os.name == 'nt':
            for k in CHECK_BIG5:
                if arg_dict[k] != None:
                    arg_dict[k] = unicode(arg_dict[k], 'big5')
    except Exception as ex:
        print(ex.message)

    mkwargs = {
    'filepath': args.filepath, 'outdir': args.outdir, 'fs_new': args.fs_new, 
    'filedir': args.filedir, 'method': args.method, 
    'interpolation_samples': args.interpolation_samples, 
    'fill_value': args.fill_value, 'round_time': args.round_time,
    'save_csv': args.save_csv, 'save_fig': args.save_fig, 
    'show_fig': args.show_fig, 'cmax_ratio': args.cmax_ratio, 
    'normalize_spec': args.normalize_spec, 'auto_adjust': args.auto_adjust,
    'cmax': args.cmax
    }

    try:
        entry(args.mission, **mkwargs)
    except Exception as ex:
        traceback.print_exc()
        print(ex.message)
