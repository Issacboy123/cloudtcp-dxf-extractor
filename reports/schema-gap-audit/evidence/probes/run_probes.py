#!/usr/bin/env python3
"""Reproduce focused schema/evaluator probes without changing verifier sources.

Usage: python run_probes.py --repo /path/to/cloudtcp-python-verifier
All generated files stay beside this script. Real-world counterexamples are
explicitly labelled hypothetical; their absent facts are never fed to evaluators.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    sys.path.insert(0, str(repo))
    from ingestion import validate_document
    from jsonschema import Draft202012Validator, FormatChecker
    from rules.full_evaluable import CAPABILITIES
    from rules.full_evaluable import EVALUATORS as FULL_EVALUATORS
    from rules.w1_evaluable import EVALUATORS as W1_EVALUATORS
    from verifier import DEFAULT_REGISTRY, W1_REGISTRY, verify_document
    root = Path(__file__).resolve().parent
    (root / 'inputs').mkdir(exist_ok=True)
    (root / 'results').mkdir(exist_ok=True)
    schema_bytes = (repo / 'tcp-intermediate-format.schema.json').read_bytes()
    validator = Draft202012Validator(json.loads(schema_bytes), format_checker=FormatChecker())
    base = {
        'format_version': '1.0.0',
        'site': {'name': 'Audit synthetic site', 'coordinate_system': 'local station',
                 'units': 'feet', 'road_name': 'Synthetic Road', 'state': 'OR'},
        'typical_application': {'type': 'lane_closure', 'direction': 'NB',
                                'posted_speed_mph': 45, 'lanes_total': 2, 'lanes_closed': 1},
        'zones': [
            {'zone_id': 'AW', 'type': 'advance_warning', 'start_station': 0, 'end_station': 500},
            {'zone_id': 'TR', 'type': 'transition', 'start_station': 500, 'end_station': 1000},
            {'zone_id': 'WK', 'type': 'work', 'start_station': 1000, 'end_station': 2000},
            {'zone_id': 'TERM', 'type': 'termination', 'start_station': 2000, 'end_station': 2200}],
        'elements': []}

    def sign(code='W20-1', station=100, element_id='S1', **extra):
        return {'element_id': element_id, 'type': 'sign', 'mutcd_code': code,
                'face_direction': 'NB', 'position': {'station': station, 'offset': 10, 'side': 'right'}, **extra}

    def taper(kind='merge', length=540, element_id='T1', width=12):
        return {'element_id': element_id, 'type': 'taper', 'taper_type': kind,
                'start_station': 500, 'end_station': 500 + length,
                'start_offset': 0, 'end_offset': width, 'lane_width_ft': 12}

    def line(spacing=60, element_id='D1'):
        return {'element_id': element_id, 'type': 'device_line', 'device': 'cone',
                'start_station': 500, 'end_station': 1000, 'start_offset': 0,
                'end_offset': 12, 'spacing_ft': spacing}

    def flagger(element_id='F1', station=700, **extra):
        return {'element_id': element_id, 'type': 'flagger', 'controls': 'NB',
                'position': {'station': station, 'offset': 8, 'side': 'right'}, **extra}

    def board(mode='flashing', element_id='A1'):
        return {'element_id': element_id, 'type': 'arrow_board', 'mode': mode,
                'position': {'station': 500, 'offset': 8, 'side': 'right'}}

    cases = []

    def add(name, elements, target, expected, *, state='OR', speed=45,
            direction='NB', ta_type='lane_closure', zones=None, categories=(), explanation=''):
        document = deepcopy(base)
        document['elements'] = deepcopy(elements)
        document['site']['state'] = state
        document['typical_application'].update(posted_speed_mph=speed, direction=direction, type=ta_type)
        if zones is not None:
            document['zones'] = deepcopy(zones)
        cases.append({'name': name, 'document': document, 'target': target,
                      'expected': expected, 'blocker_categories': list(categories), 'explanation': explanation})
        return document

    add('merge_formula_boundary', [taper()], 'TAPER-01', {'full': ['pass', True], 'w1': ['pass', True]})
    add('merge_formula_short', [taper(length=300)], 'TAPER-01', {'full': ['fail', True], 'w1': ['fail', True]})
    add('merge_formula_speed_gap', [taper()], 'TAPER-01', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, speed=42, categories=['source_policy'])
    add('shift_formula_boundary', [taper(kind='shift', length=270)], 'TAPER-02', {'full': ['pass', True], 'w1': ['pass', True]})
    add('shift_formula_speed_gap', [taper(kind='shift', length=270)], 'TAPER-02', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, speed=42, categories=['source_policy'])
    add('zero_offset_width_lane_width_fallback', [taper(width=0)], 'TAPER-01', {'full': ['not_evaluable', False], 'w1': ['pass', True]}, categories=['implementation'], explanation='The schema encodes lane_width_ft, but full registry refuses to substitute lane width for zero offset W; historical W1 does substitute.')
    add('known_taper_failure_plus_unknown_taper', [taper(length=100), taper(element_id='T2', width=0)], 'TAPER-01', {'full': ['fail', False], 'w1': ['fail', True]}, categories=['implementation'], explanation='Known failure survives an incomplete subject in full registry.')
    add('downstream_approximate_spacing', [taper(kind='downstream', length=75), line(20)], 'TAPER-03', {'w1': ['not_evaluable', False]}, categories=['schema', 'source_policy'])
    for spacing, expected in [(20, 'pass'), (60, 'not_evaluable'), (100, 'fail')]:
        add('federal_spacing_' + str(spacing), [taper(), line(spacing)], 'CHAN-01', {'full': [expected, expected != 'not_evaluable'], 'w1': [expected, expected != 'not_evaluable']}, categories=['schema'] if expected == 'not_evaluable' else ())
    add('federal_spacing_failure_plus_unknown', [taper(), line(60), line(100, 'D2')], 'CHAN-01', {'full': ['fail', False], 'w1': ['fail', False]}, categories=['schema'])
    for length, name in [(360, 'at_suggested_length'), (100, 'short_optional_buffer')]:
        zones = deepcopy(base['zones']) + [{'zone_id': 'BUF', 'type': 'upstream_buffer', 'start_station': 1100, 'end_station': 1100 + length}]
        add('buffer_' + name, [], 'BUFFER-01', {'full': ['pass', True], 'w1': ['pass', True]}, zones=zones, explanation='OPTION length affects evaluator score; it does not create a finding.')
    zones = deepcopy(base['zones']) + [{'zone_id': 'BUF', 'type': 'upstream_buffer', 'start_station': 1100, 'end_station': 1460}]
    add('buffer_unlisted_speed', [], 'BUFFER-01', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, speed=42, zones=zones, categories=['source_policy'])
    add('sign_side_explicit_facing', [sign()], 'SIGN-11', {'full': ['pass', True], 'w1': ['pass', True]})
    missing_facing = sign(); del missing_facing['face_direction']
    add('sign_side_missing_facing', [missing_facing], 'SIGN-11', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, categories=['missing_input'])
    left_sign = sign(); left_sign['position']['side'] = 'left'
    add('sign_side_exception_unmodeled', [left_sign], 'SIGN-11', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, categories=['schema', 'engineering_judgment'])
    add('sign_side_both_directions', [sign()], 'SIGN-11', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, direction='BOTH', categories=['schema'])
    zones = deepcopy(base['zones']) + [{'zone_id': 'AW2', 'type': 'advance_warning', 'start_station': 2300, 'end_station': 2600}, {'zone_id': 'TR2', 'type': 'transition', 'start_station': 2600, 'end_station': 2900}]
    add('sign_side_multiple_approaches', [sign()], 'SIGN-11', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, zones=zones, categories=['schema'])
    for label, start, end in [('zero_length', 0, 0), ('overlap', 400, 600)]:
        quality_zones = deepcopy(base['zones'])
        quality_zones[0].update(start_station=start, end_station=end)
        add('sign_side_warning_zone_' + label, [sign()], 'SIGN-11',
            {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]},
            zones=quality_zones, categories=['input_quality'],
            explanation='Geometry is representable but insufficient to establish a nondegenerate disjoint approach; distinguish validation constraints/input quality from absent schema capability.')
    add('flagger_warning_complete', [sign('W20-7'), flagger()], 'SIGN-21', {'full': ['pass', True], 'w1': ['pass', True]})
    no_controls = flagger(); del no_controls['controls']
    add('flagger_warning_missing_controls', [sign('W20-7'), no_controls], 'SIGN-21', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, categories=['missing_input'])
    no_sign_facing = sign('W20-7'); del no_sign_facing['face_direction']
    add('flagger_warning_missing_facing', [no_sign_facing, flagger()], 'SIGN-21', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, categories=['missing_input'])
    add('flagger_warning_absent', [flagger()], 'SIGN-21', {'full': ['fail', True], 'w1': ['fail', True]})
    add('flagger_warning_failure_plus_unknown', [flagger(), {**no_controls, 'element_id': 'F2'}], 'SIGN-21', {'full': ['fail', False], 'w1': ['fail', False]}, categories=['missing_input'])
    add('flagger_sight_distance_unmodeled', [flagger()], 'FLAG-02', {'w1': ['not_evaluable', False]}, categories=['schema'])
    add('sign_through_lane_applicability_unmodeled', [sign('W20-5')], 'SIGN-20', {'w1': ['not_evaluable', False]}, categories=['schema'])
    add('sign_size_road_tier_unmodeled', [sign(size_inches='48x48')], 'SIGN-31', {'w1': ['not_evaluable', False]}, categories=['schema'])
    add('arrow_shoulder_caution', [board()], 'ARROW-03', {'full': ['pass', True], 'w1': ['pass', True]}, ta_type='shoulder_closure')
    add('arrow_shoulder_arrow_mode', [board('sequential_arrow')], 'ARROW-03', {'full': ['fail', True], 'w1': ['fail', True]}, ta_type='shoulder_closure')
    add('arrow_two_lanes_no_traffic_pattern', [board()], 'ARROW-03', {'full': ['not_evaluable', False], 'w1': ['not_evaluable', False]}, categories=['schema'])
    doc = add('arrow_boards_no_lane_identity', [board(), board(element_id='A2')], 'ARROW-02', {'w1': ['not_evaluable', False]}, categories=['schema'])
    doc['typical_application'].update(lanes_total=3, lanes_closed=2)
    for state in ['OR', 'CA']:
        add('ca_taper_660_' + state.lower(), [taper(length=660)], 'CA-007', {'full': ['pass' if state == 'CA' else 'not_applicable', True]}, state=state, speed=55)
    add('ca_taper_short', [taper(length=600)], 'CA-007', {'full': ['fail', True]}, state='CA', speed=55)
    add('ca_taper_no_exact_speed_row', [taper(length=660)], 'CA-007', {'full': ['not_evaluable', False]}, state='CA', speed=52, categories=['source_policy'])
    for spacing, expected in [(20, 'pass'), (20.01, 'not_evaluable'), (100, 'not_evaluable'), (100.01, 'fail')]:
        add('ca_spacing_' + str(spacing).replace('.', '_'), [line(spacing)], 'CA-008', {'full': [expected, expected != 'not_evaluable']}, state='CA', speed=55, categories=['schema'] if expected == 'not_evaluable' else ())
    add('ca_spacing_no_exact_speed_row', [line(20)], 'CA-008', {'full': ['not_evaluable', False]}, state='CA', speed=52, categories=['source_policy'])
    add('warning_sequence_ordered', [sign(), sign('W20-5', 200, 'S2')], 'SIGN-08', {'full': ['pass', True]})
    add('warning_sequence_reversed', [sign('W20-5'), sign('W20-1', 200, 'S2')], 'SIGN-08', {'full': ['fail', True]})
    add('warning_sequence_missing_facing', [missing_facing, sign('W20-5', 200, 'S2')], 'SIGN-08', {'full': ['not_evaluable', False]}, categories=['missing_input'])
    add('warning_sequence_unknown_code', [sign(), sign('W999-999', 200, 'S2')], 'SIGN-08', {'full': ['not_evaluable', False]}, categories=['implementation'])
    add('warning_sequence_tied_station', [sign(), sign('W20-5', 100, 'S2')], 'SIGN-08', {'full': ['not_evaluable', False]}, categories=['schema', 'implementation'], explanation='Station+offset cannot establish encounter order for coincident/cross-approach signs without explicit path relationships.')
    for legend, name, expected in [('ROAD WORK NEXT 2 MILES', 'integer', 'pass'), ('ROAD WORK NEXT 2.5 MILES', 'fraction', 'fail'), ('ROAD WORK NEXT TWO MILES', 'words', 'not_evaluable'), ('', 'absent', 'not_evaluable')]:
        add('mileage_' + name, [sign('G20-1', legend=legend)], 'SIGN-26.c02', {'full': [expected, expected != 'not_evaluable']}, categories=['missing_input'] if name == 'absent' else ['implementation'] if name == 'words' else ())
    meter_doc = add('merge_formula_boundary_meters', [taper()], 'TAPER-01', {'full': ['pass', True], 'w1': ['pass', True]})
    meter_doc['site']['units'] = 'meters'
    for zone in meter_doc['zones']:
        zone['start_station'] *= .3048; zone['end_station'] *= .3048
    for element in meter_doc['elements']:
        element['start_station'] *= .3048; element['end_station'] *= .3048
    # Explicit feet fields and documented taper offsets intentionally stay feet.

    result_rows = []
    problems = []
    for case in cases:
        name, document, target = case['name'], case['document'], 'mutcd.' + case['target']
        validator.validate(document)
        validate_document(document)
        write(root / 'inputs' / (name + '.json'), document)
        output = {k: v for k, v in case.items() if k != 'document'}
        output['schema_valid'] = True
        output['registries'] = {}
        for registry_name, registry in [('full', DEFAULT_REGISTRY), ('w1', W1_REGISTRY)]:
            report = verify_document(document, registry=registry)
            focused = [r for r in report.rule_results if r.rule_id == target]
            evaluator = (FULL_EVALUATORS if registry_name == 'full' else W1_EVALUATORS).get(case['target'])
            raw_evaluator = asdict(evaluator(deepcopy(document))) if evaluator is not None else None
            record = {'input_valid': report.input_valid, 'exit_code': report.exit_code,
                      'evaluation_complete': report.evaluation_complete,
                      'status_counts': dict(Counter(r.status for r in report.rule_results)),
                      'incomplete_count': sum(not r.complete for r in report.rule_results),
                      'focused_rule_results': [asdict(r) for r in focused],
                      'raw_evaluator_result': raw_evaluator}
            output['registries'][registry_name] = record
            for r in focused:
                row = {'probe': name, 'registry': registry_name, 'rule_id': target,
                       'status': r.status, 'complete': r.complete, 'reason': r.reason,
                       'findings': len(r.findings), 'exit_code': report.exit_code,
                       'schema_valid': True, 'blocker_categories': case['blocker_categories']}
                result_rows.append(row)
            if registry_name in case['expected']:
                expected = case['expected'][registry_name]
                actual = [focused[0].status, focused[0].complete] if len(focused) == 1 else None
                if actual != expected:
                    problems.append({'probe': name, 'registry': registry_name, 'expected': expected, 'actual': actual})
        write(root / 'results' / (name + '.json'), output)

    # These probes are expected-invalid attempts to encode specific absent facts.
    # They are never counted as schema-valid evaluator counterexamples.
    invalid = []
    extension_payloads = []
    for name, field, value in [
        ('road_classification', 'road_classification', 'freeway'),
        ('operation_duration', 'duration_hours', 8),
        ('one_lane_two_way_operation', 'one_lane_two_way', True)]:
        doc = deepcopy(base); doc['typical_application'][field] = value
        extension_payloads.append((name, doc))
    doc = deepcopy(base); doc['approaches'] = [{'approach_id': 'NB', 'direction': 'NB'}]
    extension_payloads.append(('approach_inventory', doc))
    doc = deepcopy(base); doc['elements'] = [line()]; doc['elements'][0]['taper_id'] = 'T1'
    extension_payloads.append(('device_taper_association', doc))
    doc = deepcopy(base); doc['elements'] = [taper(kind='one_lane_two_way')]
    extension_payloads.append(('one_lane_two_way_taper', doc))
    doc = deepcopy(base); doc['elements'] = [flagger()]; doc['elements'][0]['available_sight_distance_ft'] = 495
    extension_payloads.append(('flagger_sight_distance', doc))
    doc = deepcopy(base); doc['elements'] = [board()]; doc['elements'][0]['closed_lane_id'] = 'L1'
    extension_payloads.append(('board_lane_association', doc))
    doc = deepcopy(base); doc['elements'] = [sign()]; doc['elements'][0]['mounting_height_ft'] = 7
    extension_payloads.append(('sign_mounting_height', doc))
    doc = deepcopy(base); doc['elements'] = [sign()]; doc['elements'][0]['placement_exception_approval'] = 'approved'
    extension_payloads.append(('sign_placement_exception', doc))
    doc = deepcopy(base); doc['elements'] = [line()]; doc['elements'][0]['device_height_inches'] = 28
    extension_payloads.append(('channelizer_physical_specification', doc))
    doc = deepcopy(base); doc['elements'] = [line()]; doc['elements'][0]['device'] = 'barricade'
    extension_payloads.append(('barricade_type', doc))
    doc = deepcopy(base); doc['elements'] = [{'element_id': 'AFAD1', 'type': 'afad', 'position': {'station': 500, 'offset': 8, 'side': 'right'}}]
    extension_payloads.append(('afad_element_type', doc))
    doc = deepcopy(base); doc['zones'][0]['accessible_route_width_ft'] = 4
    extension_payloads.append(('accessible_route_geometry', doc))
    for name, doc in extension_payloads:
        errors = sorted(validator.iter_errors(doc), key=lambda e: str(list(e.path)))
        report = verify_document(doc)
        record = {'probe': name, 'expected_schema_valid': False, 'actual_schema_valid': not errors,
                  'validation_errors': [{'path': '/' + '/'.join(map(str, e.path)), 'validator': e.validator, 'message': e.message} for e in errors],
                  'verifier_input_valid': report.input_valid, 'verifier_exit_code': report.exit_code,
                  'rules_executed': len(report.rule_results)}
        if not errors or report.input_valid or report.rule_results:
            problems.append({'probe': name, 'expected': 'invalid input with no rules executed', 'actual': record})
        write(root / 'inputs' / ('rejected_' + name + '.json'), doc)
        invalid.append(record)
    write(root / 'rejected-extensions.json', invalid)

    counterexamples = [
        {'id': 'device-taper-association', 'payload': 'federal_spacing_60',
         'world_A': '60-ft-spaced line serves the merging taper at 45 mph; S spacing limit would be exceeded.',
         'world_B': 'The same station-overlapping line serves a separate tangent path; the 2S limit permits 60 ft.',
         'missing_fact': 'Explicit device-line to taper/path association.',
         'rejected_extension': 'device_taper_association', 'runtime_rule': 'mutcd.CHAN-01'},
        {'id': 'sign-placement-exception', 'payload': 'sign_side_exception_unmodeled',
         'world_A': 'Left-side sign placement has an applicable authorized exception.',
         'world_B': 'The identical sign placement has no applicable exception.',
         'missing_fact': 'Exception applicability and supporting engineering/agency evidence.',
         'rejected_extension': 'sign_placement_exception', 'runtime_rule': 'mutcd.SIGN-11'},
        {'id': 'flagger-sight-distance', 'payload': 'flagger_sight_distance_unmodeled',
         'world_A': 'Approach alignment provides adequate sight distance to the intended stopping point.',
         'world_B': 'A crest/obstruction restricts sight distance below the applicable requirement.',
         'missing_fact': 'Approach sight-distance measurement, stopping point, and supporting design context.',
         'rejected_extension': 'flagger_sight_distance', 'runtime_rule': 'mutcd.FLAG-02'},
        {'id': 'arrow-board-lane-association', 'payload': 'arrow_boards_no_lane_identity',
         'world_A': 'The two boards are assigned distinctly to the two closed lanes.',
         'world_B': 'Both boards serve one closed lane; the other closed lane has no assigned board.',
         'missing_fact': 'Persistent lane identities and board-to-closed-lane associations; roadway applicability remains separate.',
         'rejected_extension': 'board_lane_association', 'runtime_rule': 'mutcd.ARROW-02'},
        {'id': 'sign-road-tier', 'payload': 'sign_size_road_tier_unmodeled',
         'world_A': 'The modeled sign serves a roadway tier whose applicable size row permits its dimensions.',
         'world_B': 'The identical sign serves a different roadway tier requiring a different size row.',
         'missing_fact': 'Roadway classification/size-row applicability; no numeric size threshold invented.',
         'rejected_extension': 'road_classification', 'runtime_rule': 'mutcd.SIGN-31'}]
    for pair in counterexamples:
        pair['shared_payload_sha256'] = sha256((root / 'inputs' / (pair['payload'] + '.json')).read_bytes()).hexdigest()
        pair['evidence_kind'] = 'hypothetical distinct real-world arrangements sharing one validated schema payload'
    write(root / 'counterexamples.json', counterexamples)
    write(root / 'summary.json', {'schema_sha256': sha256(schema_bytes).hexdigest(),
          'valid_probe_documents': len(cases), 'registry_executions': 2 * len(cases),
          'focused_result_rows': len(result_rows), 'rejected_extension_probes': len(invalid),
          'counterexample_pairs': len(counterexamples),
          'full_partial_evaluator_keys': sorted(k for k,v in CAPABILITIES.items() if v == 'partial'),
          'full_partial_keys_probed': sorted({c['target'] for c in cases} & {k for k,v in CAPABILITIES.items() if v == 'partial'}),
          'assertion_failures': problems})
    write(root / 'focused-results.json', result_rows)
    print(json.dumps({'valid_probes': len(cases), 'rejected_extensions': len(invalid), 'assertion_failures': problems}, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
