from backend.storage import initialize_storage, list_recent_reports, record_audit_event, record_report_run


def test_report_and_audit_persistence():
    initialize_storage()
    rid = record_report_run({'metadata': {'strategy': 'buy_and_hold'}})
    assert rid > 0
    aid = record_audit_event('report_run', {'report_id': rid})
    assert aid > 0
    reports = list_recent_reports(5)
    assert any(r['id'] == rid for r in reports)
