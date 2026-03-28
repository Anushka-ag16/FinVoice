"""
FinVoice — Angel One SmartAPI Broker Client
Handles authentication, order placement, status tracking, and portfolio sync.
"""

import logging
from datetime import datetime
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BrokerAuthError(Exception):
    """Raised when broker authentication fails."""
    pass


class BrokerOrderError(Exception):
    """Raised when order placement fails."""

    def __init__(self, message: str, broker_error: str = None):
        self.broker_error = broker_error
        super().__init__(message)


class AngelOneBroker:
    """
    Wrapper around Angel One SmartAPI for trade execution.
    Handles: login, order placement, status, holdings sync.
    """

    def __init__(self):
        self._session = None
        self._auth_token = None
        self._refresh_token = None
        self._feed_token = None
        self._connected = False

    async def login(self) -> bool:
        """
        Authenticate with Angel One using API key + TOTP.
        Must be called before any trading operations.
        """
        api_key = settings.angel_one_api_key
        client_id = settings.angel_one_client_id
        password = settings.angel_one_password
        totp_secret = settings.angel_one_totp_secret

        if not all([api_key, client_id, password, totp_secret]):
            raise BrokerAuthError(
                "Angel One credentials not configured. "
                "Set ANGEL_ONE_API_KEY, ANGEL_ONE_CLIENT_ID, "
                "ANGEL_ONE_PASSWORD, ANGEL_ONE_TOTP_SECRET in .env"
            )

        try:
            from SmartApi import SmartConnect
            import pyotp

            # Generate TOTP
            totp = pyotp.TOTP(totp_secret).now()

            # Create session
            self._session = SmartConnect(api_key=api_key)
            data = self._session.generateSession(client_id, password, totp)

            if data.get("status"):
                self._auth_token = data["data"]["jwtToken"]
                self._refresh_token = data["data"]["refreshToken"]
                self._feed_token = self._session.getfeedToken()
                self._connected = True
                logger.info(f"Angel One login successful for client {client_id}")
                return True
            else:
                raise BrokerAuthError(f"Angel One login failed: {data.get('message', 'Unknown error')}")

        except ImportError:
            raise BrokerAuthError(
                "smartapi-python not installed. Run: pip install smartapi-python pyotp"
            )
        except Exception as e:
            logger.error(f"Angel One login error: {e}")
            raise BrokerAuthError(f"Angel One authentication failed: {str(e)}")

    def _ensure_connected(self):
        """Verify we have an active session."""
        if not self._connected or not self._session:
            raise BrokerAuthError("Not connected to Angel One. Call login() first.")

    async def place_order(
        self,
        symbol: str,
        quantity: int,
        side: str,            # "BUY" or "SELL"
        order_type: str = "MARKET",
        price: float = None,
        exchange: str = "NSE",
        product_type: str = "DELIVERY",
    ) -> dict:
        """
        Place an order via Angel One SmartAPI.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE-EQ")
            quantity: Number of shares
            side: "BUY" or "SELL"
            order_type: "MARKET" or "LIMIT"
            price: Required for LIMIT orders
            exchange: "NSE" or "BSE"
            product_type: "DELIVERY" (CNC) or "INTRADAY" (MIS)

        Returns:
            dict with order_id, status, message
        """
        self._ensure_connected()

        # Get the token for the symbol
        symbol_token = await self._get_symbol_token(symbol, exchange)

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": symbol_token,
            "transactiontype": side.upper(),
            "exchange": exchange,
            "ordertype": order_type.upper(),
            "producttype": product_type,
            "duration": "DAY",
            "quantity": str(int(quantity)),
        }

        if order_type.upper() == "LIMIT" and price:
            order_params["price"] = str(price)
        else:
            order_params["price"] = "0"

        order_params["squareoff"] = "0"
        order_params["stoploss"] = "0"
        order_params["triggerprice"] = "0"

        try:
            response = self._session.placeOrder(order_params)
            logger.info(f"Order placed: {side} {quantity} {symbol} -> {response}")

            if response and response.get("status"):
                return {
                    "order_id": response["data"].get("orderid", ""),
                    "unique_order_id": response["data"].get("uniqueorderid", ""),
                    "status": "placed",
                    "message": "Order placed successfully",
                }
            else:
                error_msg = response.get("message", "Unknown error") if response else "No response from broker"
                raise BrokerOrderError(
                    f"Order rejected by broker: {error_msg}",
                    broker_error=error_msg,
                )

        except BrokerOrderError:
            raise
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            raise BrokerOrderError(f"Failed to place order: {str(e)}")

    async def get_order_status(self, order_id: str) -> dict:
        """Get current status of an order."""
        self._ensure_connected()

        try:
            order_book = self._session.orderBook()
            if order_book and order_book.get("data"):
                for order in order_book["data"]:
                    if order.get("orderid") == order_id:
                        return {
                            "order_id": order_id,
                            "status": order.get("orderstatus", "").lower(),
                            "filled_qty": float(order.get("filledshares", 0)),
                            "avg_price": float(order.get("averageprice", 0)),
                            "text": order.get("text", ""),
                        }

            return {"order_id": order_id, "status": "not_found"}

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {"order_id": order_id, "status": "error", "error": str(e)}

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> bool:
        """Cancel a pending order."""
        self._ensure_connected()

        try:
            response = self._session.cancelOrder(order_id, variety)
            if response and response.get("status"):
                logger.info(f"Order {order_id} cancelled")
                return True
            return False
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return False

    async def get_holdings(self) -> list[dict]:
        """Fetch current holdings from the broker account."""
        self._ensure_connected()

        try:
            holdings = self._session.holding()
            if holdings and holdings.get("data"):
                return [
                    {
                        "symbol": h.get("tradingsymbol", ""),
                        "quantity": int(h.get("quantity", 0)),
                        "avg_price": float(h.get("averageprice", 0)),
                        "ltp": float(h.get("ltp", 0)),
                        "pnl": float(h.get("profitandloss", 0)),
                        "exchange": h.get("exchange", "NSE"),
                    }
                    for h in holdings["data"]
                ]
            return []
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []

    async def get_ltp(self, symbols: list[str], exchange: str = "NSE") -> dict:
        """
        Get Last Traded Price for multiple symbols.
        Returns: {symbol: price}
        """
        self._ensure_connected()

        prices = {}
        for symbol in symbols:
            try:
                token = await self._get_symbol_token(symbol, exchange)
                data = self._session.ltpData(exchange, symbol, token)
                if data and data.get("data"):
                    prices[symbol] = float(data["data"].get("ltp", 0))
            except Exception as e:
                logger.warning(f"LTP fetch failed for {symbol}: {e}")
                prices[symbol] = 0.0

        return prices

    async def _get_symbol_token(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Resolve a trading symbol to its token ID.
        Angel One requires symbol tokens for API calls.
        """
        # Common NSE tokens — extend as needed
        # In production, load from Angel One's instrument list
        SYMBOL_TOKENS = {
            "RELIANCE": "2885",
            "TCS": "11536",
            "HDFCBANK": "1333",
            "INFY": "1594",
            "ICICIBANK": "4963",
            "HINDUNILVR": "1394",
            "ITC": "1660",
            "SBIN": "3045",
            "BHARTIARTL": "10604",
            "KOTAKBANK": "1922",
            "LT": "11483",
            "AXISBANK": "5900",
            "WIPRO": "3787",
            "ASIANPAINT": "236",
            "MARUTI": "10999",
            "TITAN": "3506",
            "SUNPHARMA": "3351",
            "BAJFINANCE": "317",
            "TATAMOTORS": "3456",
            "NESTLEIND": "17963",
            "POWERGRID": "14977",
            "NTPC": "11630",
            "TECHM": "13538",
            "ULTRACEMCO": "11532",
            "HEROMOTOCO": "1348",
        }

        clean_symbol = symbol.replace("-EQ", "").replace(".NS", "").upper()

        if clean_symbol in SYMBOL_TOKENS:
            return SYMBOL_TOKENS[clean_symbol]

        # Fallback: try to search via API
        logger.warning(f"Symbol token not cached for {clean_symbol}, using placeholder")
        return "0"

    async def logout(self):
        """Close the broker session."""
        if self._session and self._connected:
            try:
                self._session.terminateSession(settings.angel_one_client_id)
                logger.info("Angel One session terminated")
            except Exception as e:
                logger.warning(f"Logout error: {e}")
            finally:
                self._connected = False
                self._session = None
