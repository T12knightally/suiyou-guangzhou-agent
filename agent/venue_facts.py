"""Audited official references, not LLM-generated venue claims.

Only regular weekly rules are applied. Holidays and exceptional closures still
need a dated announcement; expired references never silently become live facts.
"""
import json
from datetime import date
from pathlib import Path

FACTS_PATH=Path(__file__).resolve().parents[1]/'config'/'venue_facts.json'

def apply_facts(place,day,today):
    catalog=json.loads(FACTS_PATH.read_text(encoding='utf-8'))
    fact=catalog['venues'].get(place['id'])
    if not fact:return place
    place['official_sources']=fact['sources']
    place['facts_checked_at']=fact['checked_at']
    age=(date.fromisoformat(today)-date.fromisoformat(fact['checked_at'][:10])).days
    if age<0 or age>catalog['max_age_days']:
        place['notice']+='；官方常规资料已过核验期'
        place['facts_status']='expired'
        return place
    place['ticket']=fact['ticket']
    place['ticket_scope']=fact['ticket_scope']
    place['reservation_required']=fact['reservation_required']
    place['reservation_note']=fact['reservation_note']
    place['official_url']=fact['sources'][0]['url']
    place['booking_url']=fact.get('booking_url')
    place['facts_status']='official_regular_rules'
    place['factual_status']='official_reference'
    # The current audit covers this normal working week only, not every future holiday.
    if fact['calendar_valid_from']<=day<=fact['calendar_valid_to']:
        place['closed']=date.fromisoformat(day).weekday() in fact['closed_weekdays']
        place['open_minutes']=fact['open_minutes']
        place['last_entry_minute']=fact.get('last_entry_minute')
        place['opening_basis']='官方常规开放规则；临时调整以公告为准'
    else:
        place['open_minutes']=None
        place['opening_basis']='超出已核对日历区间，节假日或临时开放安排需确认'
    place['notice']='；'.join([fact['ticket_scope'],fact['reservation_note'],place['opening_basis']])
    return place
