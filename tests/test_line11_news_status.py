from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.build_line11_news_status import classify_title, decide_status, segment_for


def _item(*, title: str, published_at: datetime, signal: str) -> dict[str, object]:
    return {
        "title": title,
        "published_at": published_at.isoformat(),
        "signal": signal,
        "reason": "energia" if "energia" in title.casefold() else None,
        "affected_segment": segment_for(title),
    }


def test_headline_classifier_prioritizes_recovery_over_old_problem_reference() -> None:
    assert classify_title("Linha 11-Coral volta ao normal após falha elétrica") == "normal"
    assert classify_title("Linhas 11-Coral e 12-Safira abrem normalmente após problemas") == "normal"


def test_headline_classifier_detects_current_disruption() -> None:
    assert classify_title("Falha de energia interrompe circulação da Linha 11-Coral hoje") == "disruption"
    assert classify_title("Linha 11-Coral opera com velocidade reduzida") == "attention"


def test_headline_classifier_ignores_historical_contract_context() -> None:
    assert classify_title("CPTM vai ressarcir concessionária após pane durante gestão das linhas") == "context"


def test_latest_recovery_turns_estimate_green() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    items = [
        _item(
            title="Linha 11-Coral volta ao normal após falha",
            published_at=now - timedelta(hours=2),
            signal="normal",
        ),
        _item(
            title="Falha interrompe Linha 11-Coral",
            published_at=now - timedelta(hours=4),
            signal="disruption",
        ),
    ]
    decision = decide_status(items, now)
    assert decision["color"] == "green"
    assert decision["level"] == "normal"


def test_recent_disruption_turns_estimate_red() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    items = [
        _item(
            title="Falha de energia interrompe Linha 11-Coral em Suzano",
            published_at=now - timedelta(hours=1),
            signal="disruption",
        )
    ]
    decision = decide_status(items, now)
    assert decision["color"] == "red"
    assert decision["level"] == "problem"
    assert "Suzano" in str(decision["affected_segment"])


def test_older_unresolved_disruption_becomes_yellow_not_false_red() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    items = [
        _item(
            title="Falha interrompe Linha 11-Coral",
            published_at=now - timedelta(hours=30),
            signal="disruption",
        )
    ]
    decision = decide_status(items, now)
    assert decision["color"] == "yellow"
    assert decision["level"] == "attention"


def test_no_recent_operational_headline_is_green_but_low_confidence() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    items = [
        _item(
            title="CPTM discute investimentos na Linha 11-Coral",
            published_at=now - timedelta(hours=3),
            signal="context",
        )
    ]
    decision = decide_status(items, now)
    assert decision["color"] == "green"
    assert decision["confidence"] == "baixa"
    assert "Sem alerta recente" in str(decision["status"])
