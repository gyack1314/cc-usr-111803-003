"""按名录版次计算日宰量、企业合并和周度覆盖。"""
from datetime import date, timedelta

from .ledger import entities


def _version_key(version):
    """版次按 v 加数值比较，缺失或非数字形式按文本兜底。"""
    text = str(version or '')
    digits = text[1:] if text[:1] in ('v', 'V') else text
    if digits.isdigit():
        return (1, int(digits), text)
    return (0, 0, text)


def _record_identity(record):
    """分页记录以 record_id 为身份；无 record_id 的旧格式按主体、日期与口径识别。"""
    record_id = record.get('record_id')
    if record_id:
        return ('record', record_id)
    return ('legacy', record['company_id'], record['observed_on'], record['basis'])


def merge_daily_records(reports):
    """合并多份分页日报：同一 record_id 只保留最高 record_version，重叠页不重复计数。"""
    merged = {}
    for report in sorted(reports, key=lambda item: (item['id'], _version_key(item['version']))):
        for record in report['payload']['records']:
            key = _record_identity(record)
            version = _version_key(record.get('record_version'))
            current = merged.get(key)
            if current is None or version >= current[0]:
                merged[key] = (version, record)
    return [entry[1] for entry in merged.values()]


def current_week(connection, collection):
    rows = entities(connection, collection)
    rosters = sorted((item for item in rows if item['type'] == 'plant_roster'),
                     key=lambda item: item['version'])
    reports = [item for item in rows if item['type'] == 'daily_slaughter']
    summaries = sorted((item for item in rows if item['type'] == 'weekly_summary'),
                       key=lambda item: item['version'])
    if not rosters or not reports or not summaries:
        return {'status': '资料待齐', 'plants': [], 'missing_days': [], 'estimate_heads': 0}

    roster = rosters[-1]['payload']['plants']
    transitions = {item['company_id']: item for item in roster if item['state'] == 'merged'}
    start = min(date.fromisoformat(item['payload']['week_start']) for item in reports)
    end = max(date.fromisoformat(item['payload']['week_end']) for item in reports)
    actual = {}
    estimates = {}
    observed_days = set()
    for source in merge_daily_records(reports):
        day = date.fromisoformat(source['observed_on'])
        company = source['company_id']
        transition = transitions.get(company)
        if transition and day >= date.fromisoformat(transition['effective_on']):
            company = transition['successor_id']
        target = actual if source['basis'] == 'actual' else estimates
        key = (company, source['observed_on'])
        target[key] = target.get(key, 0) + source['slaughter_heads']
        if source['basis'] == 'actual':
            observed_days.add(source['observed_on'])

    plants = []
    for company in sorted({key[0] for key in actual} | {key[0] for key in estimates}):
        actual_days = sorted(day for name, day in actual if name == company)
        estimate_heads = sum(value for (name, _), value in estimates.items() if name == company)
        plants.append({
            'company_id': company,
            'actual_heads': sum(value for (name, _), value in actual.items() if name == company),
            'actual_days': actual_days,
            'estimate_heads': estimate_heads,
        })

    expected_days = {(start + timedelta(days=offset)).isoformat()
                     for offset in range((end - start).days + 1)}
    missing_days = sorted(expected_days - observed_days)
    summary = summaries[-1]['payload']
    actual_heads = sum(actual.values())
    current_scope = sorted({item['company_id'] for item in plants})
    scope_matches = sorted(summary['scope']) == current_scope
    total_matches = summary['slaughter_heads'] == actual_heads
    complete = not missing_days and scope_matches and total_matches
    return {
        'week_start': start.isoformat(),
        'week_end': end.isoformat(),
        'actual_heads': actual_heads,
        'summary_heads': summary['slaughter_heads'],
        'missing_days': missing_days,
        'estimate_heads': sum(estimates.values()),
        'scope_matches': scope_matches,
        'total_matches': total_matches,
        'plants': plants,
        'summary_scope': sorted(summary['scope']),
        'status': '可核实' if complete else '覆盖或汇总待核',
    }
