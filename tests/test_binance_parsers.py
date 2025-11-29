from datetime import datetime

from orderflow_recorder.binance.ws_client import parse_depth_message, parse_trade_message


def test_parse_depth_message_normalizes_fields():
	raw = {
		"e": "depthUpdate",
		"E": 1700000000000,
		"s": "BTCUSDT",
		"U": 1000,
		"u": 1005,
		"b": [["35000.1", "0.5"], ["35000.0", "1.0"]],
		"a": [["35001.2", "0.4"]],
	}

	normalized = parse_depth_message(raw)

	assert normalized["source"] == "binance-futures"
	assert normalized["type"] == "orderbook"
	assert normalized["symbol"] == "BTCUSDT"
	assert isinstance(normalized["event_time"], datetime)
	assert normalized["first_update_id"] == 1000
	assert normalized["final_update_id"] == 1005
	assert normalized["bids"] == [["35000.1", "0.5"], ["35000.0", "1.0"]]
	assert normalized["asks"] == [["35001.2", "0.4"]]


def test_parse_trade_message_normalizes_fields():
	raw = {
		"e": "aggTrade",
		"E": 1700000001000,
		"a": 12345678,
		"s": "ethusdt",
		"p": "2222.50",
		"q": "0.25",
		"T": 1700000002000,
		"m": True,
	}

	normalized = parse_trade_message(raw)

	assert normalized["source"] == "binance-futures"
	assert normalized["type"] == "trade"
	assert normalized["symbol"] == "ETHUSDT"
	assert isinstance(normalized["event_time"], datetime)
	assert isinstance(normalized["trade_time"], datetime)
	assert normalized["price"] == 2222.50
	assert normalized["quantity"] == 0.25
	assert normalized["is_buyer_maker"] is True
	assert normalized["agg_trade_id"] == 12345678


