"""
한국투자증권 실시간 데이터 WebSocket 클라이언트
- 실시간 시세, 호가, 체결 데이터 수신
- 자동매매 신호 생성 및 주문 실행 연동
"""
import asyncio
import json
import websockets
import os
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KoreaInvestmentWebSocket:
    """한국투자증권 WebSocket 클라이언트"""
    
    def __init__(self):
        self.app_key = os.environ.get('KOREA_APP_KEY')
        self.app_secret = os.environ.get('KOREA_APP_SECRET')
        self.websocket_url = "ws://ops.koreainvestment.com:21000"
        
        # 실시간 데이터 핸들러들
        self.price_handler: Optional[Callable] = None
        self.orderbook_handler: Optional[Callable] = None
        self.execution_handler: Optional[Callable] = None
        
        # 구독 종목 리스트
        self.subscribed_stocks = set()
        
        # 연결 상태
        self.is_connected = False
        self.websocket = None
        
    async def connect(self):
        """WebSocket 서버에 연결"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.is_connected = True
            logger.info("WebSocket 연결 성공")
            
            # 인증 메시지 전송
            await self._authenticate()
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            raise
    
    async def _authenticate(self):
        """WebSocket 인증"""
        auth_message = {
            "header": {
                "approval_key": self.app_key,
                "custtype": "P",  # 개인
                "tr_type": "1",   # 등록
                "content-type": "utf-8"
            }
        }
        
        await self.websocket.send(json.dumps(auth_message))
        logger.info("WebSocket 인증 요청 전송")
    
    async def subscribe_price(self, stock_code: str):
        """실시간 시세 구독
        
        Args:
            stock_code: 종목코드 (6자리)
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다.")
        
        subscribe_message = {
            "header": {
                "approval_key": self.app_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0",  # 실시간시세 TR
                    "tr_key": stock_code
                }
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscribed_stocks.add(stock_code)
        logger.info(f"실시간 시세 구독: {stock_code}")
    
    async def subscribe_orderbook(self, stock_code: str):
        """실시간 호가 구독
        
        Args:
            stock_code: 종목코드 (6자리)
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다.")
        
        subscribe_message = {
            "header": {
                "approval_key": self.app_key,
                "custtype": "P", 
                "tr_type": "1",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STASP0",  # 실시간호가 TR
                    "tr_key": stock_code
                }
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        logger.info(f"실시간 호가 구독: {stock_code}")
    
    def set_price_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """실시간 시세 데이터 핸들러 설정"""
        self.price_handler = handler
    
    def set_orderbook_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """실시간 호가 데이터 핸들러 설정"""
        self.orderbook_handler = handler
    
    def set_execution_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """실시간 체결 데이터 핸들러 설정"""
        self.execution_handler = handler
    
    async def listen(self):
        """실시간 데이터 수신 루프"""
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다.")
        
        logger.info("실시간 데이터 수신 시작...")
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket 연결이 종료되었습니다.")
            self.is_connected = False
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")
            raise
    
    async def _handle_message(self, message: str):
        """수신된 메시지 처리"""
        try:
            data = json.loads(message)
            
            # TR ID에 따라 적절한 핸들러 호출
            tr_id = data.get("header", {}).get("tr_id")
            
            if tr_id == "H0STCNT0" and self.price_handler:
                # 실시간 시세 데이터
                price_data = self._parse_price_data(data)
                await self.price_handler(price_data)
                
            elif tr_id == "H0STASP0" and self.orderbook_handler:
                # 실시간 호가 데이터  
                orderbook_data = self._parse_orderbook_data(data)
                await self.orderbook_handler(orderbook_data)
                
            elif tr_id == "H0STCNI0" and self.execution_handler:
                # 실시간 체결 데이터
                execution_data = self._parse_execution_data(data)
                await self.execution_handler(execution_data)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    def _parse_price_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """실시간 시세 데이터 파싱"""
        body = data.get("body", {})
        
        return {
            "timestamp": datetime.now(),
            "stock_code": body.get("mksc_shrn_iscd"),
            "current_price": int(body.get("stck_prpr", 0)),
            "change": int(body.get("prdy_vrss", 0)),
            "change_rate": float(body.get("prdy_ctrt", 0)),
            "volume": int(body.get("acml_vol", 0)),
            "high": int(body.get("stck_hgpr", 0)),
            "low": int(body.get("stck_lwpr", 0)),
        }
    
    def _parse_orderbook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """실시간 호가 데이터 파싱"""
        body = data.get("body", {})
        
        # 매도호가 (5단계)
        ask_prices = []
        ask_volumes = []
        for i in range(1, 6):
            ask_prices.append(int(body.get(f"askp{i}", 0)))
            ask_volumes.append(int(body.get(f"askp_rsqn{i}", 0)))
        
        # 매수호가 (5단계)
        bid_prices = []
        bid_volumes = []
        for i in range(1, 6):
            bid_prices.append(int(body.get(f"bidp{i}", 0)))
            bid_volumes.append(int(body.get(f"bidp_rsqn{i}", 0)))
        
        return {
            "timestamp": datetime.now(),
            "stock_code": body.get("mksc_shrn_iscd"),
            "ask_prices": ask_prices,
            "ask_volumes": ask_volumes,
            "bid_prices": bid_prices, 
            "bid_volumes": bid_volumes,
        }
    
    def _parse_execution_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """실시간 체결 데이터 파싱"""
        body = data.get("body", {})
        
        return {
            "timestamp": datetime.now(),
            "stock_code": body.get("mksc_shrn_iscd"),
            "execution_price": int(body.get("stck_cntg_hour", 0)),
            "execution_volume": int(body.get("cntg_vol", 0)),
            "execution_time": body.get("stck_cntg_hour"),
        }
    
    async def disconnect(self):
        """WebSocket 연결 종료"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket 연결 종료")


# 사용 예제
async def example_price_handler(price_data):
    """실시간 시세 처리 예제"""
    print(f"[실시간시세] {price_data['stock_code']}: "
          f"{price_data['current_price']:,}원 "
          f"({price_data['change']:+,}, {price_data['change_rate']:+.2f}%)")

async def example_orderbook_handler(orderbook_data):
    """실시간 호가 처리 예제"""
    print(f"[실시간호가] {orderbook_data['stock_code']}: "
          f"매도1호가 {orderbook_data['ask_prices'][0]:,}원 "
          f"매수1호가 {orderbook_data['bid_prices'][0]:,}원")


if __name__ == "__main__":
    async def main():
        # WebSocket 클라이언트 생성
        ws_client = KoreaInvestmentWebSocket()
        
        # 핸들러 설정
        ws_client.set_price_handler(example_price_handler)
        ws_client.set_orderbook_handler(example_orderbook_handler)
        
        try:
            # 연결
            await ws_client.connect()
            
            # 삼성전자 실시간 데이터 구독
            await ws_client.subscribe_price("005930")
            await ws_client.subscribe_orderbook("005930")
            
            # 실시간 데이터 수신
            await ws_client.listen()
            
        except KeyboardInterrupt:
            print("사용자 중단")
        finally:
            await ws_client.disconnect()
    
    # 실행
    asyncio.run(main())