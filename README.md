# sphinxdoc-test

## Overview

This is a demo repo about how to create docs for Numpy-style docstrings by Sphinx, and host them on github.


## Structure
```
project/		# <- your project
	README.md (README.rst)
	mod_foo/	# module
		__init__.py
		foo.py
		bar.py
	docs/		# <- to store config files for sphinx to generate docs
		(empty)
	...
project-docs/	# <- docs of your project
	(empty)
```


## Thought

* Create a new branch of your repo that only contains your docs.

* It is recommended to store your docs locally in a different folder. (Like the directory structure mentioned above)

So that you don't have to switch branch before updating anything in your `project_docs`. (You just have to check them out to a branch called `gh-pages` after modification.)


## Steps 1 - create a new branch for docs

1. Create a new folder for your docs (project-docs/), and `cd` to it. Then, 

	```$ git clone git@github.com:YOUR_USER_NAME/project.git html```

	This command will clone your repo into the folder `html`.

2. Move into the folder `html` (project-docs/html/)

	```$ cd html```

	Next, we will clear the content in the folder `html`, and make it as a directory for branch `gh-pages`.

	```
	$ git symbolic-ref HEAD refs/heads/pg-pages
	$ rm .git/index
	$ git clean -fdx
	```

	These commands will create a new root branch which points to the folder `html`, and clear the content in it.


## Steps 2 - build docs by sphinx

1. Install sphinx

	```$ pip install sphinx```

2. Move into the folder for storing config files (project/docs/), then use `sphinx-quickstart`

	```
	$ cd project/docs
	$ sphinx-quickstart
	```

3. After quickstart

	a. go to `project/docs/` -> modify `Makefile`

	```
	BUILDDIR = …
	```
	↓    ↓    ↓
	```
	BUILDDIR      = ../../sphinxdoc-test-docs
	PDFBUILDDIR   = /tmp
	PDF           = ../manual.pdf
	```

	b. go to `project/docs/source/` -> add the following lines in `conf.py`

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

4. Generate docs

	```$ sphinx-apidoc -o [output_path] [project_path]```

	official doc: [sphinx-apidoc manual page](http://www.sphinx-doc.org/en/1.5.1/man/sphinx-apidoc.html)

5. Then, `mod_foo.rst`... should appear in the folder `project/docs/source/`. If not, copy and paste them into it.

6. Edit `index.rst` (under the folder `project/docs/source/`), like
	```
	Welcome to [YOUR_PROJECT_NAME]'s documentation!
	==========================================

	Contents:

	.. toctree::
	   :maxdepth: 2

	   [ADD THOSE GENERATED .rst FILES HERE]
	```

7. Remember add a `.nojekyll` file under the source folder

8. `cd` to the folder `project/docs/` (where `Makefile` locates in)  

	```$ make html```

	This command will generate html files according to the `*.rst / *.md` files in the folder `project/docs/build/`.

9. Move all content in the `project/docs/build` into the folder you want to store docs (`project-docs/`).


## Step 3 - update docs

1. Go to the folder of docs (`project-docs/`), commit all changes, and push them to github

	```
	$ git commit -a -m "First commit of docs"
	$ git push origin ph-pages
	```


## Reference

[Publishing sphinx-generated docs on github](https://daler.github.io/sphinxdoc-test/includeme.html)

[Sphinx documentation on GitHub](http://datadesk.latimes.com/posts/2012/01/sphinx-on-github/)

[Hosting your Sphinx docs in Github](http://lucasbardella.com/blog/2010/02/hosting-your-sphinx-docs-in-github)
