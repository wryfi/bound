cfitall :: configure it all
===========================

cfitall (configure it all) is a configuration management library for
python applications. It's inspired by and loosely modeled on the
excellent `viper <https://github.com/spf13/viper>`__ library for go,
though it doesn't have quite as many features (yet).

It does cover the basics of configuring your application from a variety
of sources, with a predictable inheritance hierarchy. It does this by
creating a configuration registry for your application. When
configuration data is accessed from the registry, these configuration
sources are merged together:

-  default values provided by the developer
-  configuration file values (override defaults)
-  environment variables (override configuration file values & defaults)
-  ``set()`` calls made by the developer (override everything)

This allows your application to support configuration by environment
variable or using a variety of common text formats (currently json and
yaml are supported).

Install
-------

``pip install cfitall`` should do the trick for most users. cfitall
requires python3 but otherwise has minimal dependencies.

Example
-------

This example is for a contrived application called ``myapp``.

First, set up a ``config`` module for myapp. Notice that we name our
config object ``myapp``.

::

    # myapp/config.py

    from cfitall.config import ConfigRegistry

    # create a configuration registry for myapp
    config = ConfigRegistry('myapp')

    # set some default configuration values
    config.set_default('global.name', 'my fancy application')
    config.values['defaults']['global']['foo'] = 'bar'
    config.set_default('network.listen', '127.0.0.1')

    # add a path to search for configuration files
    config.add_config_path('/Users/wryfi/.config/myapp')

    # read data from first config file found (myapp.json, myapp.yaml, or myapp.yml)
    config.read_config()

Since we named our config object ``myapp``, environment variables
beginning with ``MYAPP__`` are searched for values by cfitall.
Environment variables containing commas are interpreted as
comma-delimited lists. Export some environment variables to see this in
action:

::

    export MYAPP__GLOBAL__NAME="my app from bash"
    export MYAPP__GLOBAL__THINGS="four,five,six"
    export MYAPP__NETWORK__PORT=8080

Again, since we chose ``myapp`` as our config object name, our
configuration file is also named ``myapp.(json|yaml|yml)``. Create a
configuration file in YAML or JSON and put it in one of the paths you
added to your config registry:

::

    # ~/.config/myapp/myapp.yml
    global:
      bar: foo
      things:
        - one
        - two
        - three
      person:
        name: joe
        hair: brown
    network:
      port: 9000
      listen: '*'

Now you can use your config object to get the configuration data you
need. You can access the merged configuration data by its configuration
key (dotted path notation), or you can just grab the entire merged
dictionary via the ``dict`` property.

::

    # myapp/logic.py

    from config import config

    # prints $MYAPP__GLOBAL__THINGS because env var overrides config file
    print(config.get('global.things', list))

    # prints $MYAPP__NETWORK__PORT because env var overrides config file
    print(config.get('network.port', int))

    # prints '*' from myapp.yml because config file overrides default
    print(config.get('network.listen', str))

    # prints 'joe' from myapp.yml because it is only defined there
    print(config.get('global.person.name', str))

    # alternate way to print joe through the config dict property
    print(config.dict['global']['person']['name'])

    # prints the entire assembled config as dictionary
    print(config.dict)

Running ``logic.py`` should go something like this:

::

    $ python logic.py
    ['four', 'five', 'six']
    8080
    *
    joe
    joe
    {'global': {'name': 'my app from bash', 'foo': 'bar', 'bar': 'foo', 'things': ['four', 'five', 'six'], 'person': {'name': 'joe', 'hair': 'brown'}}, 'network': {'listen': '*', 'port': '8080'}}

Notes
-----

-  Avoid using ``__`` (double-underscore) in your configuration variable
   keys (names), as cfitall uses ``__`` as a hierarchical delimiter when
   parsing environment variables.
-  If you must use ``__`` in variable keys, you can pass an
   ``env_separator`` argument with a different string to the
   ConfigRegistry constructor, e.g.
   ``config =     ConfigRegistry(env_separator='____')``.
-  Environment variables matching the pattern ``MYAPP__.*`` are
   automatically read into the configuration, where ``MYAPP`` refers to
   the uppercase ``name`` given to your ConfigRegistry at creation.
-  You can customize this behavior by passing an ``env_prefix`` value
   and/or ``env_separator`` as kwargs to the ConfigRegistry constructor.

