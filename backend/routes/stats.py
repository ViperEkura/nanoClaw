"""Token statistics API routes"""
from datetime import date, timedelta
from flask import Blueprint, request, g
from sqlalchemy import func
from backend.models import TokenUsage
from backend.utils.helpers import ok, err

bp = Blueprint("stats", __name__)


@bp.route("/api/stats/tokens", methods=["GET"])
def token_stats():
    """Get token usage statistics"""
    user = g.current_user
    period = request.args.get("period", "daily")
    
    today = date.today()
    
    if period == "daily":
        stats = TokenUsage.query.filter_by(user_id=user.id, date=today).all()
        result = {
            "period": "daily",
            "date": today.isoformat(),
            "prompt_tokens": sum(s.prompt_tokens for s in stats),
            "completion_tokens": sum(s.completion_tokens for s in stats),
            "total_tokens": sum(s.total_tokens for s in stats),
            "by_model": {
                s.model: {
                    "prompt": s.prompt_tokens,
                    "completion": s.completion_tokens,
                    "total": s.total_tokens
                } for s in stats
            }
        }
    elif period == "weekly":
        start_date = today - timedelta(days=6)
        stats = TokenUsage.query.filter(
            TokenUsage.user_id == user.id,
            TokenUsage.date >= start_date,
            TokenUsage.date <= today
        ).all()
        
        result = _build_period_result(stats, "weekly", start_date, today, 7)
    elif period == "monthly":
        start_date = today - timedelta(days=29)
        stats = TokenUsage.query.filter(
            TokenUsage.user_id == user.id,
            TokenUsage.date >= start_date,
            TokenUsage.date <= today
        ).all()
        
        result = _build_period_result(stats, "monthly", start_date, today, 30)
    else:
        return err(400, "invalid period")
    
    return ok(result)


def _build_period_result(stats, period, start_date, end_date, days):
    """Build result for period-based statistics"""
    daily_data = {}
    for s in stats:
        d = s.date.isoformat()
        if d not in daily_data:
            daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}
        daily_data[d]["prompt"] += s.prompt_tokens
        daily_data[d]["completion"] += s.completion_tokens
        daily_data[d]["total"] += s.total_tokens
    
    # Fill missing dates
    for i in range(days):
        d = (end_date - timedelta(days=days - 1 - i)).isoformat()
        if d not in daily_data:
            daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "prompt_tokens": sum(s.prompt_tokens for s in stats),
        "completion_tokens": sum(s.completion_tokens for s in stats),
        "total_tokens": sum(s.total_tokens for s in stats),
        "daily": daily_data
    }
