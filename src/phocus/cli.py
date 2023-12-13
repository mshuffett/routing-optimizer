"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mphocus` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``phocus.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``phocus.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import json

import click

from phocus.app import plan_route


@click.command()
@click.argument('input-file')
def main(input_file):
    click.echo('Running optimizer with input file: %s' % input_file)
    with open(input_file) as f:
        j = json.load(f)

    result = plan_route(j)
