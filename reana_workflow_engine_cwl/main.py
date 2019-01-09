# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2017, 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Workflow Engine CWL main."""

from __future__ import absolute_import, print_function, unicode_literals

import json
import logging
import os
import sys
from io import BytesIO

import cwltool.main
import pkg_resources
from cwltool.context import LoadingContext

from reana_workflow_engine_cwl.__init__ import __version__
from reana_workflow_engine_cwl.config import SHARED_VOLUME_PATH
from reana_workflow_engine_cwl.context import REANARuntimeContext
from reana_workflow_engine_cwl.cwl_reana import ReanaPipeline
from reana_workflow_engine_cwl.database import SQLiteHandler

log = logging.getLogger("reana-workflow-engine-cwl")
log.setLevel(logging.INFO)
console = logging.StreamHandler()
log.addHandler(console)


def versionstring():
    """Return string with cwltool version."""
    pkg = pkg_resources.require("cwltool")
    if pkg:
        cwltool_ver = pkg[0].version
    else:
        cwltool_ver = "unknown"
    return "%s %s with cwltool %s" % (sys.argv[0], __version__, cwltool_ver)


def main(workflow_uuid, workflow_spec, workflow_inputs,
         operational_options, working_dir, publisher, **kwargs):
    """Run main method."""
    working_dir = os.path.join(SHARED_VOLUME_PATH, working_dir)
    os.chdir(working_dir)
    log.info("Dumping workflow specification and input parameter files...")
    with open("workflow.json", "w") as f:
        json.dump(workflow_spec, f)
    with open("inputs.json", "w") as f:
        json.dump(workflow_inputs, f)
    total_commands = 0
    print('workflow_spec:', workflow_spec)
    if '$graph' in workflow_spec:
        total_commands = len(workflow_spec['$graph'])
    total_jobs = {"total": total_commands - 1, "job_ids": []}
    initial_job_state = {"total": 0, "job_ids": []}
    running_jobs = initial_job_state
    finished_jobs = initial_job_state
    failed_jobs = initial_job_state
    publisher.publish_workflow_status(
        workflow_uuid, 1,
        logs='',
        message={
            "progress": {
                "total": total_jobs,
                "running": running_jobs,
                "finisned": finished_jobs,
                "failed": failed_jobs
            }})
    tmpdir = os.path.join(working_dir, "cwl/tmpdir")
    tmp_outdir = os.path.join(working_dir, "cwl/outdir")
    os.makedirs(tmpdir)
    os.makedirs(tmp_outdir)
    args = operational_options
    args = args + [
        "--debug",
        "--tmpdir-prefix", tmpdir + "/",
        "--tmp-outdir-prefix", tmp_outdir + "/",
        "--default-container", "frolvlad/alpine-bash",
        "--outdir", os.path.join(os.path.dirname(working_dir), "outputs"),
        "workflow.json#main", "inputs.json"]
    log.error("parsing arguments ...")
    parser = cwltool.main.arg_parser()
    parsed_args = parser.parse_args(args)

    if not len(args) >= 1:
        print(versionstring())
        print("CWL document required, no input file was provided")
        parser.print_usage()
        return 1

    if parsed_args.version:
        print(versionstring())
        return 0

    if parsed_args.quiet:
        log.setLevel(logging.WARN)
    if parsed_args.debug:
        log.setLevel(logging.DEBUG)

    pipeline = ReanaPipeline()
    log.error("starting the run..")
    db_log_writer = SQLiteHandler(workflow_uuid, publisher)

    f = BytesIO()
    cwl_arguments = vars(parsed_args)
    runtimeContext = REANARuntimeContext(workflow_uuid, working_dir,
                                         publisher, pipeline,
                                         **cwl_arguments)
    result = cwltool.main.main(
        args=parsed_args,
        executor=pipeline.executor,
        loadingContext=LoadingContext(
            {'construct_tool_object': pipeline.make_tool}),
        runtimeContext=runtimeContext,
        versionfunc=versionstring,
        logger_handler=db_log_writer,
        stdout=f
    )
    publisher.publish_workflow_status(workflow_uuid, 2,
                                      f.getvalue().decode("utf-8"))
    return result
