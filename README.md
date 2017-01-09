# sphinxdoc-test

## Overview  
This is a demo repo about how to create docs by Sphinx (Numpy-style), and host them on github.  

## Structure  
```
project/
	README.md (README.rst)
	mod_foo/	# module
		__init__.py
		foo.py
		bar.py
	docs/
		(empty)
```

## Steps

1. Install sphinx  

2. Use `sphinx-quickstart`  

	a. ``` $ cd project/docs```  

	b. ``` $ sphinx-quickstart```  

	ref: 
	[Publishing sphinx-generated docs on github](https://daler.github.io/sphinxdoc-test/includeme.html)
	[Sphinx documentation on GitHub](http://datadesk.latimes.com/posts/2012/01/sphinx-on-github/)
	[Hosting your Sphinx docs in Github](http://lucasbardella.com/blog/2010/02/hosting-your-sphinx-docs-in-github)

3. After quickstart  

	a. go to `docs/` -> modify `Makefile`  

	```
	BUILDDIR = …
	```
	↓    ↓    ↓
	```
	BUILDDIR      = ../../sphinxdoc-test-docs
	PDFBUILDDIR   = /tmp
	PDF           = ../manual.pdf
	```

	b. go to `docs/source` -> add the following lines in `conf.py`

	* import clauses:
	```
	import os
	import sys
	sys.path.insert(0, os.path.abspath("../.."))
	import project	# name of your module
	```
	* extension clauses:
	```
	extensions = [
		'sphinx.ext.autodoc',
		'sphinx.ext.napoleon'	# <- make sphinx be able to parse numpy-docstring
	]
	```

4. Generate api-doc

	``` $ sphinx-apidoc -o [output_path] [project_path]```

	official doc: [sphinx-apidoc manual page](http://www.sphinx-doc.org/en/1.5.1/man/sphinx-apidoc.html)

5. Then, `mod_foo.rst`... should appear under the folder `docs/source`. If not, copy and paste them into it.

6. Edit `index.rst` (under the folder `docs/source/`), like
	```
	Welcome to [YOUR_PROJECT_NAME]'s documentation!
	==========================================

	Contents:

	.. toctree::
	   :maxdepth: 2

	   [ADD THOSE GENERATED .rst FILES HERE]
	```

7. Remember add a `.nojekyll` file under the source folder

8. `cd` to the folder `project/docs` (where `Makefile` locates)  

	``` $ make html```

9. Upload this repo on github, and you can see the docs on github pages.  

	url of your repo: `https://github.com/YOUR_NAME/YOUR_REPO`

	url of the github pages: `https://YOUR_NAME.github.com/YOUR_REPO`
