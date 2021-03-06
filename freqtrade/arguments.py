"""
This module contains the argument manager class
"""

import argparse
import os
import re
from typing import List, NamedTuple, Optional
import arrow
from freqtrade import __version__, constants


class TimeRange(NamedTuple):
    """
    NamedTuple Defining timerange inputs.
    [start/stop]type defines if [start/stop]ts shall be used.
    if *type is none, don't use corresponding startvalue.
    """
    starttype: Optional[str] = None
    stoptype: Optional[str] = None
    startts: int = 0
    stopts: int = 0


class Arguments(object):
    """
    Arguments Class. Manage the arguments received by the cli
    """

    def __init__(self, args: List[str], description: str) -> None:
        self.args = args
        self.parsed_arg: Optional[argparse.Namespace] = None
        self.parser = argparse.ArgumentParser(description=description)

    def _load_args(self) -> None:
        self.common_args_parser()
        self._build_subcommands()

    def get_parsed_arg(self) -> argparse.Namespace:
        """
        Return the list of arguments
        :return: List[str] List of arguments
        """
        if self.parsed_arg is None:
            self._load_args()
            self.parsed_arg = self.parse_args()

        return self.parsed_arg

    def parse_args(self) -> argparse.Namespace:
        """
        Parses given arguments and returns an argparse Namespace instance.
        """
        parsed_arg = self.parser.parse_args(self.args)

        # Workaround issue in argparse with action='append' and default value
        # (see https://bugs.python.org/issue16399)
        if parsed_arg.config is None:
            parsed_arg.config = [constants.DEFAULT_CONFIG]

        return parsed_arg

    def common_args_parser(self) -> None:
        """
        Parses given common arguments and returns them as a parsed object.
        """
        self.parser.add_argument(
            '-v', '--verbose',
            help='Verbose mode (-vv for more, -vvv to get all messages).',
            action='count',
            dest='loglevel',
            default=0,
        )
        self.parser.add_argument(
            '--logfile',
            help='Log to the file specified',
            dest='logfile',
            type=str,
            metavar='FILE'
        )
        self.parser.add_argument(
            '--version',
            action='version',
            version=f'%(prog)s {__version__}'
        )
        self.parser.add_argument(
            '-c', '--config',
            help='Specify configuration file (default: %(default)s). '
                 'Multiple --config options may be used.',
            dest='config',
            action='append',
            type=str,
            metavar='PATH',
        )
        self.parser.add_argument(
            '-d', '--datadir',
            help='Path to backtest data.',
            dest='datadir',
            default=None,
            type=str,
            metavar='PATH',
        )
        self.parser.add_argument(
            '-s', '--strategy',
            help='Specify strategy class name (default: %(default)s).',
            dest='strategy',
            default='DefaultStrategy',
            type=str,
            metavar='NAME',
        )
        self.parser.add_argument(
            '--strategy-path',
            help='Specify additional strategy lookup path.',
            dest='strategy_path',
            type=str,
            metavar='PATH',
        )
        self.parser.add_argument(
            '--dynamic-whitelist',
            help='Dynamically generate and update whitelist'
                 ' based on 24h BaseVolume (default: %(const)s).'
                 ' DEPRECATED.',
            dest='dynamic_whitelist',
            const=constants.DYNAMIC_WHITELIST,
            type=int,
            metavar='INT',
            nargs='?',
        )
        self.parser.add_argument(
            '--db-url',
            help='Override trades database URL, this is useful if dry_run is enabled'
                 ' or in custom deployments (default: %(default)s).',
            dest='db_url',
            type=str,
            metavar='PATH',
        )
        self.parser.add_argument(
            '--sd-notify',
            help='Notify systemd service manager.',
            action='store_true',
            dest='sd_notify',
        )

    @staticmethod
    def optimizer_shared_options(parser: argparse.ArgumentParser) -> None:
        """
        Parses given common arguments for Backtesting, Edge and Hyperopt modules.
        :param parser:
        :return:
        """
        parser.add_argument(
            '-i', '--ticker-interval',
            help='Specify ticker interval (1m, 5m, 30m, 1h, 1d).',
            dest='ticker_interval',
            type=str,
        )
        parser.add_argument(
            '--timerange',
            help='Specify what timerange of data to use.',
            default=None,
            type=str,
            dest='timerange',
        )
        parser.add_argument(
            '--max_open_trades',
            help='Specify max_open_trades to use.',
            default=None,
            type=int,
            dest='max_open_trades',
        )
        parser.add_argument(
            '--stake_amount',
            help='Specify stake_amount.',
            default=None,
            type=float,
            dest='stake_amount',
        )
        parser.add_argument(
            '-r', '--refresh-pairs-cached',
            help='Refresh the pairs files in tests/testdata with the latest data from the '
                 'exchange. Use it if you want to run your optimization commands with '
                 'up-to-date data.',
            action='store_true',
            dest='refresh_pairs',
        )

    @staticmethod
    def backtesting_options(parser: argparse.ArgumentParser) -> None:
        """
        Parses given arguments for Backtesting module.
        """
        parser.add_argument(
            '--eps', '--enable-position-stacking',
            help='Allow buying the same pair multiple times (position stacking).',
            action='store_true',
            dest='position_stacking',
            default=False
        )
        parser.add_argument(
            '--dmmp', '--disable-max-market-positions',
            help='Disable applying `max_open_trades` during backtest '
                 '(same as setting `max_open_trades` to a very high number).',
            action='store_false',
            dest='use_max_market_positions',
            default=True
        )
        parser.add_argument(
            '-l', '--live',
            help='Use live data.',
            action='store_true',
            dest='live',
        )
        parser.add_argument(
            '--strategy-list',
            help='Provide a commaseparated list of strategies to backtest '
                 'Please note that ticker-interval needs to be set either in config '
                 'or via command line. When using this together with --export trades, '
                 'the strategy-name is injected into the filename '
                 '(so backtest-data.json becomes backtest-data-DefaultStrategy.json',
            nargs='+',
            dest='strategy_list',
        )
        parser.add_argument(
            '--export',
            help='Export backtest results, argument are: trades. '
                 'Example --export=trades',
            type=str,
            default=None,
            dest='export',
        )
        parser.add_argument(
            '--export-filename',
            help='Save backtest results to this filename \
                  requires --export to be set as well\
                  Example --export-filename=user_data/backtest_data/backtest_today.json\
                  (default: %(default)s)',
            type=str,
            default=os.path.join('user_data', 'backtest_data', 'backtest-result.json'),
            dest='exportfilename',
            metavar='PATH',
        )

    @staticmethod
    def edge_options(parser: argparse.ArgumentParser) -> None:
        """
        Parses given arguments for Edge module.
        """
        parser.add_argument(
            '--stoplosses',
            help='Defines a range of stoploss against which edge will assess the strategy '
                 'the format is "min,max,step" (without any space).'
                 'example: --stoplosses=-0.01,-0.1,-0.001',
            type=str,
            dest='stoploss_range',
        )

    @staticmethod
    def hyperopt_options(parser: argparse.ArgumentParser) -> None:
        """
        Parses given arguments for Hyperopt module.
        """
        parser.add_argument(
            '--customhyperopt',
            help='Specify hyperopt class name (default: %(default)s).',
            dest='hyperopt',
            default=constants.DEFAULT_HYPEROPT,
            type=str,
            metavar='NAME',
        )
        parser.add_argument(
            '--eps', '--enable-position-stacking',
            help='Allow buying the same pair multiple times (position stacking).',
            action='store_true',
            dest='position_stacking',
            default=False
        )
        parser.add_argument(
            '--dmmp', '--disable-max-market-positions',
            help='Disable applying `max_open_trades` during backtest '
                 '(same as setting `max_open_trades` to a very high number).',
            action='store_false',
            dest='use_max_market_positions',
            default=True
        )
        parser.add_argument(
            '-e', '--epochs',
            help='Specify number of epochs (default: %(default)d).',
            dest='epochs',
            default=constants.HYPEROPT_EPOCH,
            type=int,
            metavar='INT',
        )
        parser.add_argument(
            '-s', '--spaces',
            help='Specify which parameters to hyperopt. Space separate list. \
                  Default: %(default)s.',
            choices=['all', 'buy', 'sell', 'roi', 'stoploss'],
            default='all',
            nargs='+',
            dest='spaces',
        )
        parser.add_argument(
            '--print-all',
            help='Print all results, not only the best ones.',
            action='store_true',
            dest='print_all',
            default=False
        )
        parser.add_argument(
            '-j', '--job-workers',
            help='The number of concurrently running jobs for hyperoptimization '
                 '(hyperopt worker processes). '
                 'If -1 (default), all CPUs are used, for -2, all CPUs but one are used, etc. '
                 'If 1 is given, no parallel computing code is used at all.',
            dest='hyperopt_jobs',
            default=-1,
            type=int,
            metavar='JOBS',
        )
        parser.add_argument(
            '--random-state',
            help='Set random state to some positive integer for reproducible hyperopt results.',
            dest='hyperopt_random_state',
            default=None,
            type=Arguments.check_int_positive,
            metavar='INT',
        )

    def _build_subcommands(self) -> None:
        """
        Builds and attaches all subcommands
        :return: None
        """
        from freqtrade.optimize import backtesting, hyperopt, edge_cli

        subparsers = self.parser.add_subparsers(dest='subparser')

        # Add backtesting subcommand
        backtesting_cmd = subparsers.add_parser('backtesting', help='Backtesting module.')
        backtesting_cmd.set_defaults(func=backtesting.start)
        self.optimizer_shared_options(backtesting_cmd)
        self.backtesting_options(backtesting_cmd)

        # Add edge subcommand
        edge_cmd = subparsers.add_parser('edge', help='Edge module.')
        edge_cmd.set_defaults(func=edge_cli.start)
        self.optimizer_shared_options(edge_cmd)
        self.edge_options(edge_cmd)

        # Add hyperopt subcommand
        hyperopt_cmd = subparsers.add_parser('hyperopt', help='Hyperopt module.')
        hyperopt_cmd.set_defaults(func=hyperopt.start)
        self.optimizer_shared_options(hyperopt_cmd)
        self.hyperopt_options(hyperopt_cmd)

    @staticmethod
    def parse_timerange(text: Optional[str]) -> TimeRange:
        """
        Parse the value of the argument --timerange to determine what is the range desired
        :param text: value from --timerange
        :return: Start and End range period
        """
        if text is None:
            return TimeRange(None, None, 0, 0)
        syntax = [(r'^-(\d{8})$', (None, 'date')),
                  (r'^(\d{8})-$', ('date', None)),
                  (r'^(\d{8})-(\d{8})$', ('date', 'date')),
                  (r'^-(\d{10})$', (None, 'date')),
                  (r'^(\d{10})-$', ('date', None)),
                  (r'^(\d{10})-(\d{10})$', ('date', 'date')),
                  (r'^(-\d+)$', (None, 'line')),
                  (r'^(\d+)-$', ('line', None)),
                  (r'^(\d+)-(\d+)$', ('index', 'index'))]
        for rex, stype in syntax:
            # Apply the regular expression to text
            match = re.match(rex, text)
            if match:  # Regex has matched
                rvals = match.groups()
                index = 0
                start: int = 0
                stop: int = 0
                if stype[0]:
                    starts = rvals[index]
                    if stype[0] == 'date' and len(starts) == 8:
                        start = arrow.get(starts, 'YYYYMMDD').timestamp
                    else:
                        start = int(starts)
                    index += 1
                if stype[1]:
                    stops = rvals[index]
                    if stype[1] == 'date' and len(stops) == 8:
                        stop = arrow.get(stops, 'YYYYMMDD').timestamp
                    else:
                        stop = int(stops)
                return TimeRange(stype[0], stype[1], start, stop)
        raise Exception('Incorrect syntax for timerange "%s"' % text)

    @staticmethod
    def check_int_positive(value) -> int:
        try:
            uint = int(value)
            if uint <= 0:
                raise ValueError
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{value} is invalid for this parameter, should be a positive integer value"
            )
        return uint

    def scripts_options(self) -> None:
        """
        Parses given arguments for scripts.
        """
        self.parser.add_argument(
            '-p', '--pairs',
            help='Show profits for only this pairs. Pairs are comma-separated.',
            dest='pairs',
            default=None
        )

    def testdata_dl_options(self) -> None:
        """
        Parses given arguments for testdata download
        """
        self.parser.add_argument(
            '--pairs-file',
            help='File containing a list of pairs to download.',
            dest='pairs_file',
            default=None,
            metavar='PATH',
        )

        self.parser.add_argument(
            '--export',
            help='Export files to given dir.',
            dest='export',
            default=None,
            metavar='PATH',
        )

        self.parser.add_argument(
            '-c', '--config',
            help='Specify configuration file (default: %(default)s). '
                 'Multiple --config options may be used.',
            dest='config',
            action='append',
            type=str,
            metavar='PATH',
        )

        self.parser.add_argument(
            '--days',
            help='Download data for given number of days.',
            dest='days',
            type=int,
            metavar='INT',
            default=None
        )

        self.parser.add_argument(
            '--exchange',
            help='Exchange name (default: %(default)s). Only valid if no config is provided.',
            dest='exchange',
            type=str,
            default='bittrex'
        )

        self.parser.add_argument(
            '-t', '--timeframes',
            help='Specify which tickers to download. Space separated list. \
                  Default: %(default)s.',
            choices=['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h',
                     '6h', '8h', '12h', '1d', '3d', '1w'],
            default=['1m', '5m'],
            nargs='+',
            dest='timeframes',
        )

        self.parser.add_argument(
            '--erase',
            help='Clean all existing data for the selected exchange/pairs/timeframes.',
            dest='erase',
            action='store_true'
        )
