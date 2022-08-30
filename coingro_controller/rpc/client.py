import json
import logging
from typing import Any, Dict
from urllib.parse import urlencode, urlparse, urlunparse

import requests
from coingro.exceptions import TemporaryError
from coingro.misc import retrier


logger = logging.getLogger(__name__)


class CoingroClient:
    def __init__(self, config: Dict[str, Any]):
        self._session = requests.Session()
        if ('cg_api_server_username' in config) and ('cg_api_server_password' in config):
            username = config['cg_api_server_username']
            password = config['cg_api_server_password']
            self._session.auth = (username, password)

    @retrier(retries=3, sleep_time=1)
    def _call(self, method, serverurl, apipath, params: dict = None, data=None, files=None):

        if str(method).upper() not in ('GET', 'POST', 'PUT', 'DELETE'):
            raise ValueError(f'invalid method <{method}>')
        basepath = f"{serverurl}/{apipath}"

        hd = {"Accept": "application/json",
              "Content-Type": "application/json"
              }

        # Split url
        schema, netloc, path, par, query, fragment = urlparse(basepath)
        # URLEncode query string
        query = urlencode(params) if params else ""
        # recombine url
        url = urlunparse((schema, netloc, path, par, query, fragment))

        try:
            resp = self._session.request(method, url, headers=hd, data=json.dumps(data))
            # return resp.text
            return resp.json()
        except Exception as e:
            raise TemporaryError(e)

    def _get(self, serverurl, apipath, params: dict = None):
        return self._call("GET", serverurl, apipath, params=params)

    def _delete(self, serverurl, apipath, params: dict = None):
        return self._call("DELETE", serverurl, apipath, params=params)

    def _post(self, serverurl, apipath, params: dict = None, data: dict = None):
        return self._call("POST", serverurl, apipath, params=params, data=data)

    def _put(self, serverurl, apipath, params: dict = None, data: dict = None):
        return self._call("PUT", serverurl, apipath, params=params, data=data)

    def start(self, serverurl):
        """Start the bot if it's in the stopped state.

        :return: json object
        """
        return self._post(serverurl, "start")

    def stop(self, serverurl):
        """Stop the bot. Use `start` to restart.

        :return: json object
        """
        return self._post(serverurl, "stop")

    def stopbuy(self, serverurl):
        """Stop buying (but handle sells gracefully). Use `reload_config` to reset.

        :return: json object
        """
        return self._post(serverurl, "stopbuy")

    def reload_config(self, serverurl):
        """Reload configuration.

        :return: json object
        """
        return self._post(serverurl, "reload_config")

    def balance(self, serverurl):
        """Get the account balance.

        :return: json object
        """
        return self._get(serverurl, "balance")

    def count(self, serverurl):
        """Return the amount of open trades.

        :return: json object
        """
        return self._get(serverurl, "count")

    def locks(self, serverurl):
        """Return current locks

        :return: json object
        """
        return self._get(serverurl, "locks")

    def delete_lock(self, serverurl, lock_id, pair=None):
        """Delete (disable) lock from the database.

        :param lock_id: ID for the lock to delete
        :return: json object
        """
        if pair:
            data = {'lockid': lock_id, 'pair': pair}
            return self._post(serverurl, "locks/delete", data=data)
        else:
            return self._delete(serverurl, f"locks/{lock_id}")

    def daily(self, serverurl, days=None):
        """Return the profits for each day, and amount of trades.

        :return: json object
        """
        return self._get(serverurl, "daily", params={"timescale": days} if days else None)

    def edge(self, serverurl):
        """Return information about edge.

        :return: json object
        """
        return self._get(serverurl, "edge")

    def profit(self, serverurl):
        """Return the profit summary.

        :return: json object
        """
        return self._get(serverurl, "profit")

    def stats(self, serverurl):
        """Return the stats report (durations, sell-reasons).

        :return: json object
        """
        return self._get(serverurl, "stats")

    def performance(self, serverurl):
        """Return the performance of the different coins.

        :return: json object
        """
        return self._get(serverurl, "performance")

    def status(self, serverurl):
        """Get the status of open trades.

        :return: json object
        """
        return self._get(serverurl, "status")

    def version(self, serverurl):
        """Return the version of the bot.

        :return: json object containing the version
        """
        return self._get(serverurl, "version")

    def show_config(self, serverurl):
        """
        Returns part of the configuration, relevant for trading operations.
        :return: json object containing the version
        """
        return self._get(serverurl, "show_config")

    def ping(self, serverurl):
        """simple ping"""
        return self._get(serverurl, "ping")
        # configstatus = self.show_config(serverurl)
        # if not configstatus:
        #     return {"status": "not_running"}
        # elif configstatus['state'] == "running":
        #     return {"status": "pong"}
        # else:
        #     return {"status": "not_running"}

    def logs(self, serverurl, limit=None):
        """Show latest logs.

        :param limit: Limits log messages to the last <limit> logs. No limit to get the entire log.
        :return: json object
        """
        return self._get(serverurl, "logs", params={"limit": limit} if limit else 0)

    def trades(self, serverurl, limit=None, offset=None):
        """Return trades history, sorted by id

        :param limit: Limits trades to the X last trades. Max 500 trades.
        :param offset: Offset by this amount of trades.
        :return: json object
        """
        params = {}
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset
        return self._get(serverurl, "trades", params=params)

    def trade(self, serverurl, trade_id):
        """Return specific trade

        :param trade_id: Specify which trade to get.
        :return: json object
        """
        return self._get(serverurl, f"trade/{trade_id}")

    def delete_trade(self, serverurl, trade_id):
        """Delete trade from the database.
        Tries to close open orders. Requires manual handling of this asset on the exchange.

        :param trade_id: Deletes the trade with this ID from the database.
        :return: json object
        """
        return self._delete(serverurl, f"trades/{trade_id}")

    def whitelist(self, serverurl):
        """Show the current whitelist.

        :return: json object
        """
        return self._get(serverurl, "whitelist")

    def blacklist(self, serverurl, *args):
        """Show the current blacklist.

        :param add: List of coins to add (example: "BNB/BTC")
        :return: json object
        """
        if not args:
            return self._get(serverurl, "blacklist")
        else:
            return self._post(serverurl, "blacklist", data={"blacklist": args})

    def delete_blacklist(self, serverurl, pairs):
        """Show the current blacklist.

        :param add: List of coins to add (example: "BNB/BTC")
        :return: json object
        """
        params = []
        for pair in pairs:
            params.append(('pairs_to_delete', pair))
        return self._delete(serverurl, "blacklist", params=params)

    def forceenter(self,
                   serverurl,
                   pair,
                   side=None,
                   price=None,
                   ordertype=None,
                   stakeamount=None,
                   entry_tag=None):
        """Buy an asset.

        :param pair: Pair to buy (ETH/BTC)
        :param side: Optional - 'long' or 'short'
        :param price: Optional - price to buy
        :param ordertype: Optional - 'limit' or 'market'
        :param stakeamount: Optional - lot size
        :param entry_tag: Optional - string label of entry reason
        :return: json object of the trade
        """
        data = {"pair": pair,
                "price": price,
                "side": side,
                "ordertype": ordertype,
                "stakeamount": stakeamount,
                "entry_tag": entry_tag
                }
        return self._post(serverurl, "forceenter", data=data)

    def forceexit(self, serverurl, tradeid, ordertype=None):
        """Force-exit a trade.

        :param tradeid: Id of the trade (can be received via status command)
        :param ordertype: Optional - 'limit' or 'market'
        :return: json object
        """
        data = {"tradeid": tradeid,
                "ordertype": ordertype
                }
        return self._post(serverurl, "forceexit", data=data)

    def strategies(self, serverurl):
        """Lists available strategies

        :return: json object
        """
        return self._get(serverurl, "strategies")

    def strategy(self, serverurl, strategy):
        """Get strategy details

        :param strategy: Strategy class name
        :return: json object
        """
        return self._get(serverurl, f"strategy/{strategy}")

    def plot_config(self, serverurl):
        """Return plot configuration if the strategy defines one.

        :return: json object
        """
        return self._get(serverurl, "plot_config")

    def available_pairs(self, serverurl, timeframe=None, stake_currency=None):
        """Return available pair (backtest data) based on timeframe / stake_currency selection

        :param timeframe: Only pairs with this timeframe available.
        :param stake_currency: Only pairs that include this timeframe
        :return: json object
        """
        return self._get(serverurl, "available_pairs", params={
            "stake_currency": stake_currency if timeframe else '',
            "timeframe": timeframe if timeframe else '',
        })

    def pair_candles(self, serverurl, pair, timeframe, limit=None):
        """Return live dataframe for <pair><timeframe>.

        :param pair: Pair to get data for
        :param timeframe: Only pairs with this timeframe available.
        :param limit: Limit result to the last n candles.
        :return: json object
        """
        return self._get(serverurl, "pair_candles", params={
            "pair": pair,
            "timeframe": timeframe,
            "limit": limit,
        })

    def pair_history(self, serverurl, pair, timeframe, strategy, timerange=None):
        """Return historic, analyzed dataframe

        :param pair: Pair to get data for
        :param timeframe: Only pairs with this timeframe available.
        :param strategy: Strategy to analyze and get values for
        :param timerange: Timerange to get data for (same format than --timerange endpoints)
        :return: json object
        """
        return self._get(serverurl, "pair_history", params={
            "pair": pair,
            "timeframe": timeframe,
            "strategy": strategy,
            "timerange": timerange if timerange else '',
        })

    def sysinfo(self, serverurl):
        """Provides system information (CPU, RAM usage)

        :return: json object
        """
        return self._get(serverurl, "sysinfo")

    def health(self, serverurl):
        """Provides info on last process

        :return: json object
        """
        return self._get(serverurl, "health")

    def state(self, serverurl):
        """Provides information on running state

        :return: json object
        """
        return self._get(serverurl, "state")

    def exchange(self, serverurl, exchange_name):
        """Info on a single exchange

        :param exchange_name: Name of exchange
        :return: json object
        """
        return self._get(serverurl, f"exchange/{exchange_name}")

    def settings_options(self, serverurl):
        """Configuration options

        :return: json object
        """
        return self._get(serverurl, "settings_options")

    def update_exchange(self, serverurl,
                        dry_run=None,
                        name=None,
                        key=None,
                        secret=None,
                        password=None,
                        uid=None):
        """Update exchange configuration

        :param dry_run: Boolean indicating if the bot run in dry-run mode.
        :param name: Exchange name.
        :param key: API key (only required in live mode).
        :param secret: API secret key (only required in live mode).
        :param password: Password (depends on exchange).
        :param uid: UID (depends on exchange).
        :return: json object
        """
        return self._post(serverurl, "exchange", data={
            "dry_run": dry_run,
            "name": name,
            "key": key,
            "secret": secret,
            "password": password,
            "uid": uid,
        })

    def update_strategy(self, serverurl,
                        strategy=None,
                        minimal_roi=None,
                        stoploss=None,
                        trailing_stop=None,
                        trailing_stop_positive=None,
                        trailing_stop_positive_offset=None,
                        trailing_only_offset_is_reached=None):
        """Update strategy configuration

        :param strategy: The strategy the bot should use.
        :param minimal_roi: Json object representing the minimal roi in the form {"<mins>": <roi>}.
        :param stoploss: Fractional loss at which to close trades (negative float).
        :param trailing_stop: boolean indicating if a trailing stoploss should be utilised.
        :param trailing_stop_positive: Fraction behind highest observed price at which to set the
            trailing stoploss.
        :param trailing_stop_positive_offset: Fraction indicating price increase required for
            trailing stoploss to be activated.
        :param trailing_only_offset_is_reached: Should the positive offset be used.
        :return: json object
        """
        return self._post(serverurl, "strategy", data={
            "strategy": strategy,
            "minimal_roi": minimal_roi,
            "stoploss": stoploss,
            "trailing_stop": trailing_stop,
            "trailing_stop_positive": trailing_stop_positive,
            "trailing_stop_positive_offset": trailing_stop_positive_offset,
            "trailing_only_offset_is_reached": trailing_only_offset_is_reached,
        })

    def update_settings(self, serverurl,
                        max_open_trades=None,
                        stake_currency=None,
                        stake_amount=None,
                        tradable_balance_ratio=None,
                        fiat_display_currency=None,
                        available_capital=None,
                        dry_run_wallet=None):
        """Update general configuration

        :param max_open_trades: Maximum number of trades that can be open simultaneously
            (-1 for infinite).
        :param stake_currency: Stake currency for trading.
        :param stake_amount: Amount of stake currency entered into each trade.
        :param tradable_balance_ratio: Ratio of starting balance available for trading.
        :param fiat_display_currency: Currency used to display perfomance metrics.
        :param available_capital: Starting capital available to the bot (useful for running more
            than one coingro instance on the same account).
        :param dry_run_wallet: Starting value of simulated stake currency
            (only used in dry-run mode).
        :return: json object
        """
        return self._post(serverurl, "settings", data={
            "max_open_trades": max_open_trades,
            "stake_currency": stake_currency,
            "stake_amount": stake_amount,
            "tradable_balance_ratio": tradable_balance_ratio,
            "fiat_display_currency": fiat_display_currency,
            "available_capital": available_capital,
            "dry_run_wallet": dry_run_wallet,
        })

    def reset_original_config(self, serverurl):
        """Reset the configuration to its original state

        :return: json object
        """
        return self._post(serverurl, "reset_original_config")

    def timeunit_profit(self, serverurl, timeunit=None, timescale=1):
        """Return the profits for a time frame, and amount of trades.

        :return: json object
        """
        if timeunit not in ['weeks', 'months']:
            timeunit = 'days'
        return self._get(serverurl, "timeunit_profit", params={
                'timeunit': timeunit,
                'timescale': timescale,
            })

    def trade_summary(self, serverurl):
        """Return the profits for multiple timeframes.

        :return: json object
        """
        return self._get(serverurl, "trade_summary")
