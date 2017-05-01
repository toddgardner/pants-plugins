# Pants-plugins

A set of open sourced plugins for the pants build system.

Current Plugins:

* verst.pants.s3cache - an artifact cache based on s3.
* verst.pants.docker - docker integration for pants.
* verst.pants.ensime - An updated ensime generator, installed under ensime-verst
* verst.pants.k8s - Tools for controlling k8s from pants (currently can clone namespaces)
* verst.pants.resources - Adds an absolute_resources target, which places references with 
* verst.pants.scalastyle - adds scalastyle to compile, with a soft failure mode
* verst.pants.slick - adds a slick_gen rule for generating slick from the repo.
* verst.pants.specs2 - add a specs2_tests rule for running specs2 files directly.
* verst.pants.yoyo - apply Yoyo migrations from the repo.

Note: all but the first two were just added to the repo, and still need some tests and pypi packages.

## Installation

It's intended for these to be distributed via pypi. However, at the moment there's some problems with installing plugins, so you may need to copy these source files into your repo.

The current issues with plugins are:

* If you're on a pre-release version of 1.3.0, it'll cause resolution issues ([this](https://github.com/pantsbuild/pex/pull/373) and [this](https://github.com/pantsbuild/pex/pull/374))
* If you use the s3plugin, the boto dependency will be problematic: see [here](https://github.com/pantsbuild/pants/issues/4428)

So you can use pypi but only if on a stable pants release and using verst.pants.docker.

I've included both instructions below.

### Pypi

Change your pants.ini

```
[GLOBAL]
plugin_version: 1.1.1

plugins: +[
    "verst.pants.docker==%(plugin_version)s",
  ]

# Install the packages
backend_packages: +[
    "verst.pants.docker",
  ]
```

### Copying to Repo

On the other hand, if you want to copy the files:

```
# Copy the files to your checkout.
cp -R ../pants-plugins/src/python/verst src/python/
# You can remove the BUILD files if you want, since it'll be executed inside pants.
find src/python/verst/ -name BUILD -type f -exec rm {} \;
```

Change your pants.ini

```
[GLOBAL]
# If you haven't already you need to add this to your python path to pick up in repo modules
pythonpath: +[
    "%(buildroot)s/src/python",
  ]

# Install the packages
backend_packages: +[
    "verst.pants.docker",
  ]
```

## Plugins

### verst.pants.s3cache

An artifact cache based on using S3 as a backend.

In addition to the above installation, you'll need to install the requirements into the pants venv. See an [altered pants setup script](pants.extrareqs)

Add something like this to your pants.ini

```
# To read and write everything, set below. Realistically you probably want to
# cache from your continuous integration machines and might only want some
# steps cached.
[cache]
read_from: [
    "%(buildroot)s/.local_artifact_cache/",
    "s3://some-bucket-name/some-path"
  ]
write_to: [
    "%(buildroot)s/.local_artifact_cache/",
    "s3://some-bucket-name/some-path"
  ]
```

It'll use [boto config](http://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration) by default, but if you want special limited credentials you can add a java properties file at ~/.pants/.s3credentials like:

```
accessKey = onething
secretKey = oranother
```

It's done as a java properties file so you can also use it in an ivy s3 resolver, like [this one](https://github.com/ActionIQ/s3-ivy-resolver); that way s3 can be both your artifact cache and a repository.

### verst.pants.docker

Docker integration for pants.

This adds two new build targets, `docker_python_image` and `docker_jvm_app_image`:

```
docker_python_image(
  name='some_python_image',
  image_name='somerepo/some-other-test',
  # You can specify a common python base image in pants.ini also.
  base_image='python:2.7',
  dependencies=[
    # This must be a python_binary
    ':some_python_binary',
  ],
)

docker_jvm_app_image(
  name='some_java_image',
  image_name='somerepo/some-test',
  # You can specify a common java base image in pants.ini also.
  base_image='openjdk:8',
  dependencies=[
    # This must be a jvm_app
    ':some_jvm_app',
  ],
)
```

You can `bundle` these targets to create the image, `run` them to do `docker run` and `docker-publish` them to a remote repo.

#### Known Issues

1. When running `./pants bundle` you can only have one python_binary in your target list or this will fail until this is merged [see here](https://github.com/pantsbuild/pants/pull/3993)
