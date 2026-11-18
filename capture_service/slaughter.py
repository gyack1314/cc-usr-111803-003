"""按名录版次计算日宰量、企业合并和周度覆盖。"""
from datetime import date, timedelta

from .ledger import entities


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
    report = reports[-1]['payload']
    start = date.fromisoformat(report['week_start'])
    end = date.fromisoformat(report['week_end'])
    actual = {}
    estimates = {}
    observed_days = set()
    for source in reports[-1]['payload']['records']:
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
        'week_start': report['week_start'],
        'week_end': report['week_end'],
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
