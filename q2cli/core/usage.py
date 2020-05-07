# ----------------------------------------------------------------------------
# Copyright (c) 2016-2020, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import textwrap
import itertools

from qiime2.core.type.primitive import Bool

import qiime2.sdk.usage as usage
from qiime2 import Metadata
from qiime2.sdk.util import (
    is_metadata_type,
    is_metadata_column_type,
    is_visualization_type,
)

from q2cli.util import to_cli_name
from q2cli.util import to_snake_case


class CLIUsage(usage.Usage):
    def __init__(self):
        super().__init__()
        self._recorder = []
        self._init_data_refs = dict()

    def _init_data_(self, ref, factory):
        self._init_data_refs[ref] = factory
        return ref

    def _merge_metadata_(self, ref, records):
        return records

    def _get_metadata_column_(self, ref, record, column_name):
        return column_name

    def _comment_(self, text: str):
        self._recorder.append('# %s' % (text,))

    def _action_(self, action, input_opts, output_opts):
        t = self._template_action(action, input_opts, output_opts)
        self._recorder.append(t)
        return output_opts

    def _assert_has_line_matching_(self, ref, label, path, expression):
        pass

    def render(self):
        return '\n'.join(self._recorder)

    def get_example_data(self):
        return {r: f() for r, f in self._init_data_refs.items()}

    def _extract_from_signature(self, action_sig):
        params, mds = [], []
        for param, spec in action_sig.parameters.items():
            if is_metadata_type(spec.qiime_type):
                mds.append((param, spec))
            else:
                params.append((param, spec))
        return params, mds

    def _template_action(self, action, input_opts, outputs):
        action_f, action_sig = action.get_action()
        cmd = to_cli_name(f"qiime {action_f.plugin_id} {action_f.id}")
        params, mds = self._extract_from_signature(action_sig)
        inputs_t = self._template_inputs(action_sig, input_opts)
        params_t = self._template_parameters(params, input_opts)
        mds_t = self._template_metadata(mds, input_opts)
        outputs_t = self._template_outputs(action_sig, outputs)
        templates = [inputs_t, params_t, mds_t, outputs_t]
        action_t = self._format_templates(cmd, templates)
        return action_t

    # TODO: revisit this signature
    def _format_templates(self, command, templates):
        wrapper = textwrap.TextWrapper(initial_indent=" " * 4)
        templates = itertools.chain(*templates)
        templates = map(wrapper.fill, templates)
        action_t = [command] + list(templates)
        action_t = " \\\n".join(action_t)
        return action_t

    def _template_inputs(self, action_sig, input_opts):
        inputs = []
        for input_ in action_sig.inputs:
            if input_ in input_opts:
                flag = to_cli_name(input_)
                # TODO: should the val be transformed to cli name, too?
                val = input_opts[input_]
                inputs.append(f"--i-{flag} {val}.qza")
        return inputs

    def _template_parameters(self, params, input_opts):
        params_t = []
        for param, spec in params:
            val = str(input_opts[param]) if param in input_opts else ""
            if spec.qiime_type is Bool:
                prefix = f"--p-" if val == "True" else f"--p-no-"
                p = f"{prefix}{to_cli_name(param)}"
                params_t.append(p)
            elif val:
                params_t.append(f"--p-{to_cli_name(param)} {val}")
        return params_t

    def _template_metadata(self, mds, input_opts):
        mds_t = []
        print(input_opts)
        # TODO: okay, I think the easiest way to get what we need is to modify
        # the scope records to include an `origin` field, that will let us
        # make some decisions on what to do with a value, based on it's origin.
        # for example, if a record came from a `get_metadata_column`, then we can
        # assume one thing, if it came from an `init_data` call, we can assume another
        # (and also use the action sig to further refine that assumption)
        for md, spec in mds:
            print(md, spec)
        return mds_t

    def _template_outputs(self, action_sig, outputs):
        outputs_t = []
        for i, spec in action_sig.outputs.items():
            qtype = spec.qiime_type
            ext = ".qzv" if is_visualization_type(qtype) else ".qza"
            p = f"--o-{to_cli_name(i)}"
            val = f"{to_snake_case(outputs[i])}{ext}"
            outputs_t.append(f"{p} {val}")
        return outputs_t

def examples(action):
    all_examples = []
    for i in action.examples:
        use = CLIUsage()
        action.examples[i](use)
        example = use.render()
        comment = f"# {i}".replace('_', ' ')
        all_examples.append(comment)
        all_examples.append(f"{example}\n")
    return "\n\n".join(all_examples)
