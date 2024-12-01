# Import system libraries
import os
import sys

# Import toml library
import toml
from toml import TomlDecodeError

# Import click library
import click

# Import Pyntel4004 functionality
from assembler.assemble import assemble
from disassembler.disassemble import disassemble
from executer.execute import execute
from executer.exe_supporting import retrieve
from hardware.processor import Processor
from shared.shared import print_messages


class Error(Exception):
    """Base class for other exceptions"""


class ConfigFileNotFound(Error):
    """Exception for when the configuration file specified cannot be found"""


class BadFormat(Error):
    """Exception for when the configuration file is badly formatted"""


def excepthook(exc, value, traceback):
    print(value)


def check_quiet(quiet, configuration):
    if quiet is None:
        return configuration.get("quiet", False)
    return True


def check_exec(exec, configuration):
    if exec is None:
        return configuration.get("exec", False)
    return True


def check_inst(inst):
    if inst is None:
        inst = 4096
    elif not (1 <= inst <= 4096):
        raise click.BadOptionUsage("--inst", "Instructions should be between 1 and 4096")
    return inst


def check_monitor(monitor, configuration):
    if monitor is None:
        return configuration.get("monitor", False)
    return True


def check_dis_content(configuration, object, inst, labels):
    object_file = configuration.get("object", object)
    if object_file is None:
        raise click.BadOptionUsage("--object/--config", "No object file specified\n")
    inst = configuration.get("inst", inst)
    labels = configuration.get("labels", labels)
    return object_file, inst, labels


def check_asm_content(configuration, input_file, output, type_type):
    input_file = configuration.get("input", input_file)
    output = configuration.get("output", output)
    type_type = configuration.get("type", type_type)
    if not input_file and output == 'default' and type_type == ('None',):
        raise click.BadOptionUsage("--config", "Empty 'asm' section in configuration file\n")
    return input_file, output, type_type


def check_type(type_type):
    valid_types = {'ALL', 'OBJ', 'H', 'BIN'}
    type_set = {t.upper() for t in type_type}
    if not type_set.issubset(valid_types):
        raise click.BadOptionUsage("--type", "Invalid output type specified\n")
    if 'ALL' in type_set and type_set != {'ALL'}:
        raise click.BadOptionUsage("--type", "'ALL' cannot be combined with other types\n")


def get_config(toml_file: str):
    try:
        with open(toml_file) as f:
            return toml.load(f)
    except FileNotFoundError:
        raise ConfigFileNotFound(f"Configuration file '{toml_file}' not found.")
    except TomlDecodeError:
        raise BadFormat(f"Configuration file '{toml_file}' is badly formatted.")


@click.group()
@click.help_option('--help', '-h')
@click.pass_context
def cli(ctx):
    """
    Command Line Interface (CLI) for Pyntel4004,
    a virtual Intel© 4004 processor written in Python.
    """
    pass


@cli.command()
@click.option('--input', '-i', help='4004 assembler source code.', type=str, metavar='<filename>')
@click.option('--output', '-o', help='4004 output file (without extension).', default='default', metavar='<filename>')
@click.option('--exec', '-x', is_flag=True, help='Execute program', default=None)
@click.option('--quiet', '-q', is_flag=True, default=None, help='Output on/off')
@click.option('--monitor', '-m', is_flag=True, default=None, help='Monitor on/off')
@click.option('--type', '-t', multiple=True, default=['None'], metavar='<extension>', help='Output types (bin/obj/h/ALL)')
@click.option('--config', '-c', metavar='<filename>', help='Configuration file', default=None)
@click.help_option('--help', '-h')
def asm(input, output, exec, monitor, quiet, type, config):
    """Assemble the input file"""
    input_file = input
    type_type = type

    if config:
        configuration = get_config(config).get("asm", {})
        input_file, output, type_type = check_asm_content(configuration, input_file, output, type_type)
        exec = check_exec(exec, configuration)
        monitor = check_monitor(monitor, configuration)
        quiet = check_quiet(quiet, configuration)

    chip = Processor()
    if quiet and monitor:
        raise click.BadParameter("--quiet and --monitor cannot be used together\n")
    if type_type == ('None',):
        raise click.BadOptionUsage("--type", "No output type specified\n")
    check_type(type_type)
    result = assemble(input_file, output, chip, quiet, str(type_type))
    if result and exec:
        print_messages(quiet, 'EXEC', chip, '')
        did_execute = execute(chip, 'rom', 0, monitor, quiet)
        if did_execute:
            print_messages(quiet, 'BLANK', chip, '')
            print_messages(quiet, 'ACC', chip, '')
            print_messages(quiet, 'CARRY', chip, '')
            print_messages(quiet, 'BLANK', chip, '')


@cli.command()
@click.option('--object', '-o', help='4004 object or binary file (specify extension)', metavar='<filename>', type=str)
@click.option('--inst', '-i', help='Instructions to disassemble', metavar='<Between 1 & 4096>', type=int)
@click.option('--labels', '-l', help='Show label table', is_flag=True, default=False)
@click.option('--config', '-c', metavar='<filename>', help='Configuration file', default=None)
@click.help_option('--help', '-h')
def dis(object, inst, labels, config) -> None:
    """Disassemble the input file"""
    object_file = object
    if config:
        configuration = get_config(config).get("dis", {})
        object_file, inst, labels = check_dis_content(configuration, object, inst, labels)
    inst = check_inst(inst)
    chip = Processor()
    memory_space, _, lbls = retrieve(object_file, chip, False)
    disassemble(chip, memory_space, 0, inst, labels, lbls)


@cli.command()
@click.option('--object', '-o', help='4004 object or binary file (specify extension)', metavar='<filename>', type=str)
@click.option('--quiet', '-q', is_flag=True, help='Output on/off')
@click.option('--config', '-c', metavar='<filename>', help='Configuration file', default=None)
@click.help_option('--help', '-h')
def exe(object, quiet, config):
    """Execute the object file"""
    if config:
        configuration = get_config(config).get("exe", {})
        object = configuration.get("object", object)
        quiet = check_quiet(quiet, configuration)
    chip = Processor()
    memory_space, _, _ = retrieve(object, chip, quiet)
    execute(chip, memory_space, 0, False, quiet)


if __name__ == '__main__':
    cli()
