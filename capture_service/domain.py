"""解析来源身份及本项目公开资料字段。"""
import json
from datetime import date
from pathlib import Path
CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'docs'/'source-contract.json').read_text(encoding='utf-8'))
def decode(raw,receipt):
    doc=json.loads(raw.decode('utf-8'))
    if not all(k in doc for k in ('kind','id','revision')): raise ValueError('资料身份缺失')
    kind=doc['kind']
    if kind not in CONTRACT['roles']: raise ValueError('未知来源类型')
    if any(k not in doc for k in CONTRACT['required_fields'][kind]): raise ValueError('来源业务字段缺失')
    if kind == 'plant_roster':
        if not doc['plants'] or any(not all(k in item for k in ('company_id','state','successor_id','effective_on'))
                                     for item in doc['plants']):
            raise ValueError('企业名录缺少主体状态或合并关系')
        if any(item['state'] not in ('active','merged') for item in doc['plants']):
            raise ValueError('企业主体状态无效')
    if kind == 'daily_slaughter':
        if not doc['records'] or any(not all(k in item for k in ('company_id','observed_on','slaughter_heads','basis'))
                                     for item in doc['records']):
            raise ValueError('日公告缺少主体、日期、宰量或口径')
        if any(item['basis'] not in ('actual','estimate') for item in doc['records']):
            raise ValueError('日公告口径无效')
        for item in doc['records']:
            date.fromisoformat(item['observed_on'])
    return [{'type':kind,'id':doc['id'],'version':doc['revision'],'payload':{k:v for k,v in doc.items() if k not in ('kind','id','revision')}}]
def assess(rows):
    """核对名录、逐日生产记录和同周汇总是否描述同一主体范围。"""
    rosters=sorted((r for r in rows if r['type']=='plant_roster'),key=lambda r:r['version'])
    daily=sorted((r for r in rows if r['type']=='daily_slaughter'),key=lambda r:r['version'])
    summaries=sorted((r for r in rows if r['type']=='weekly_summary'),key=lambda r:r['version'])
    pairs=[]
    for roster in rosters:
        ids={item['company_id'] for item in roster['payload']['plants']}
        for report in daily:
            records=report['payload']['records']
            if any(item['company_id'] in ids for item in records):
                for summary in summaries:
                    if (summary['payload']['week_start']==report['payload']['week_start'] and
                            summary['payload']['week_end']==report['payload']['week_end']):
                        pairs.append({'roster_source':roster['source'],'daily_source':report['source'],
                                      'summary_source':summary['source']})
    return {'publishable':bool(pairs),'reasons':[] if pairs else ['同一有效主体范围的日宰量与周度汇总'],
            'received_types':sorted({r['type'] for r in rows}),
            'received_versions':len(rows),'matched_pairs':pairs,
            'candidate_relations':sorted({str(r['payload'].get(CONTRACT['relation_field'])) for r in rows})}
