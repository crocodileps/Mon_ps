"""
Routes Telegram Bot
"""
from fastapi import APIRouter
import os

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.get("/test")
async def test_telegram_config():
    """Vérifier la configuration Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    return {
        "status": "configured" if (token and chat_id) else "missing_config",
        "token_present": bool(token),
        "chat_id_present": bool(chat_id),
        "chat_id": chat_id if chat_id else None
    }


@router.post("/send-test-alert")
async def send_test_alert():
    """Envoyer une alerte de test sur Telegram"""
    from services.telegram_bot import get_telegram_bot
    
    bot = get_telegram_bot()
    
    test_opportunity = {
        'id': 'test_001',
        'match': 'PSG vs Olympique Marseille',
        'odds': 2.15,
        'edge': 8.7,
        'kelly_stake': 127,
        'agent_name': 'Agent B+',
        'expected_clv': 5.2,
        'confidence': 87,
        'sharpe': 2.8,
        'risk_level': 'LOW',
        'analysis': 'Test alert',
        'time_until_start': '2h30'
    }
    
    await bot.send_opportunity_alert(test_opportunity)
    
    return {
        "status": "sent",
        "message": "Alerte envoyée sur Telegram"
    }
