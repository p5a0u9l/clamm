#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

""" """
# local
import clamm.tui

def clamm():
    """ entrance point for clamm """
    args = tui.parse_inputs().parse_args()

    # retrieve the parsed cmd/sub/... and evaluate
    funky = tui.functers[args.cmd + args.sub_cmd]
    funky(args)

