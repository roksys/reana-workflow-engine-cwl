# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2017, 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Workflow Engine CWL tasks."""

from __future__ import absolute_import, print_function

import click
import json
import logging

from reana_commons.publisher import WorkflowStatusPublisher

from reana_workflow_engine_cwl import main

log = logging.getLogger(__name__)
outputs_dir_name = 'outputs'
known_dirs = ['inputs', 'logs', outputs_dir_name]


def load_json(ctx, param, value):
    """Callback function for click option"""
    return json.loads(value)

@click.command()
@click.option('--workflow-uuid',
              required=True,
              help='UUID of workflow to be run.')
@click.option('--workflow-workspace',
              required=True,
              help='Name of workspace in which workflow should run.')
@click.option('--workflow-json',
              help='JSON representation of workflow object to be run.',
              callback=load_json)
@click.option('--workflow-parameters',
              help='JSON representation of parameters received by'
                   ' the workflow.',
              callback=load_json)
@click.option('--operational-options',
              help='Options to be passed to the workflow engine'
                   ' (i.e. caching).',
            callback=load_json)

def run_cwl_workflow(workflow_uuid, workflow_workspace,
                     workflow_json=None,
                     workflow_parameters=None,
                     operational_options={}):
    """Run cwl workflow."""
    log.info('running workflow on context: {0}'.format(locals()))
    try:
        publisher = WorkflowStatusPublisher()
        main.main(workflow_uuid, workflow_json, workflow_parameters,
                  operational_options, workflow_workspace, publisher)
        log.info('workflow done')
        publisher.publish_workflow_status(workflow_uuid, 2)
    except Exception as e:
        log.error('workflow failed: {0}'.format(e))
        publisher.publish_workflow_status(workflow_uuid, 3, message=str(e))
    finally:
        publisher.close()
