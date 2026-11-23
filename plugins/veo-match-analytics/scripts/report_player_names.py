"""Personalize report mentions using explicit team context and confirmed athlete links."""
import argparse
import copy
import json
import re

JERSEY = re.compile(r'(?<![\w#])(?:Jersey\s*#\s*|No\.\s*|number\s+|#\s*)(\d{1,2})(?!\d)', re.IGNORECASE)


def personalize_reports(reports, mentions, confirmed_links):
    links = {}
    for link in confirmed_links:
        key = (link['team'], link['jersey_number'])
        if not link.get('athlete_slug') or not link.get('player_name') or not link.get('lineup_id'):
            raise ValueError('A report name requires a confirmed fixture lineup/athlete link')
        value = (link['player_name'], link['athlete_slug'])
        if key in links and links[key] != value:
            raise ValueError('Conflicting confirmed athlete mappings')
        links[key] = value
    scopes = {}
    for mention in mentions:
        key = (mention['report_id'], mention['block_index'], mention['occurrence'])
        if key in scopes:
            raise ValueError('Duplicate mention context')
        scopes[key] = mention.get('team')
    output = copy.deepcopy(reports)
    consumed = set()
    for report in output:
        original = copy.deepcopy(report.get('source_blocks', report['blocks']))
        report['source_blocks'] = original
        report['blocks'] = copy.deepcopy(original)
        substitutions = []
        for index, block in enumerate(report['blocks']):
            text = block.get('text', '')
            replacements = []
            for occurrence, match in enumerate(JERSEY.finditer(text)):
                key = (report['id'], index, occurrence)
                if key not in scopes:
                    raise ValueError('Every jersey mention needs verified team context, including unresolved mentions')
                consumed.add(key)
                team = scopes[key]
                jersey = int(match.group(1))
                identity = links.get((team, jersey)) if team else None
                if not identity:
                    continue
                name, slug = identity
                replacements.append((match.start(), match.end(), name))
                substitutions.append({'block_index': index, 'occurrence': occurrence,
                    'source_text': match.group(0), 'source_jersey_number': jersey,
                    'team': team, 'player_name': name, 'athlete_slug': slug})
            for start, end, name in reversed(replacements):
                text = text[:start] + name + text[end:]
            block['text'] = text
        report['identity_substitutions'] = substitutions
    if consumed != set(scopes):
        raise ValueError('Mention context does not match current source report')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='JSON object containing reports, mentions, and confirmed_links')
    args = parser.parse_args()
    with open(args.input) as source: data = json.load(source)
    json.dump(personalize_reports(**data), __import__('sys').stdout, ensure_ascii=False, indent=2)
    print()
