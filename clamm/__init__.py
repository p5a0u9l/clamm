#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

""" entrance point for clamm --> CLassical Music Manager """

# local
import clamm.tui


def main():
    args = clamm.tui.parse_inputs().parse_args()

    # retrieve the parsed cmd/sub/... and evaluate
    functor = clamm.tui.functors[args.cmd + args.sub_cmd]
    functor(args)
