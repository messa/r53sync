#!/usr/bin/env python3

import argparse
import boto3
import click
from datetime import datetime
import logging
from pprint import pprint
import yaml


logger = logging.getLogger(__name__)


@click.group()
def main():
    setup_logging()

@main.command()
def zones():
    r53 = Route53()
    zones = r53.list_zones()
    print_zone_table(zones)

@main.command()
@click.argument('zone_name')
def records(zone_name):
    r53 = Route53()
    rrsets = r53.list_zone_rrsets(zone_name)
    print_rrset_table(rrsets)

@main.command()
@click.argument('zone_name')
def dump(zone_name):
    r53 = Route53()
    rrsets = r53.list_zone_rrsets(zone_name)
    d = dump_rrsets(zone_name, rrsets)
    print(yaml.dump(d))


@main.command()
@click.argument('filename')
def diff(filename):
    file_data = yaml.load(open(filename).read())
    r53 = Route53()
    rrsets = r53.list_zone_rrsets(file_data['zone'])
    print_diff(file_data, rrsets)


@main.command()
@click.argument('filename')
def sync(filename):
    file_data = yaml.load(open(filename).read())
    r53 = Route53()
    rrsets = r53.list_zone_rrsets(file_data['zone'])
    sync_records(r53, file_data, rrsets)


def setup_logging():
    if 0:
        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s: %(message)s')
        logging.getLogger('botocore').setLevel(logging.INFO)
        logging.getLogger('botocore.vendored.requests').setLevel(logging.WARNING)


class Route53:

    def __init__(self):
        self.client = boto3.client('route53')
        self.logger = logger.getChild(self.__class__.__name__)
        self._zone_name_id_cache = {}

    def get_zone_id_from_name(self, zone_name):
        if zone_name not in self._zone_name_id_cache:
            result = self.client.list_hosted_zones_by_name(DNSName=zone_name, MaxItems='1')
            hzs = [hz for hz in result['HostedZones'] if hz['Name'] == zone_name]
            if not hzs:
                raise Exception('Hosted zone {!r} not found'.format(zone_name))
            if len(hzs) > 1:
                # should not happen
                raise Exception('More than 1 hosted zone found for name {!r}'.format(zone_name))
            hz, = hzs
            self.logger.debug('Zone %r has id %r', zone_name, hz['Id'])
            self._zone_name_id_cache[zone_name] = hz['Id']
        return self._zone_name_id_cache[zone_name]

    def list_zone_rrsets(self, zone_name):
        zone_id = self.get_zone_id_from_name(zone_name)
        all_rrsets = []
        extra_kwargs = {}
        while True:
            self.logger.debug('list_resource_record_sets %r %r', zone_id, extra_kwargs)
            result = self.client.list_resource_record_sets(HostedZoneId=zone_id, MaxItems='100', **extra_kwargs)
            all_rrsets.extend(result['ResourceRecordSets'])
            if result.get('IsTruncated'):
                extra_kwargs = {
                    'StartRecordName': result['NextRecordName'],
                    'StartRecordType': result['NextRecordType'],
                }
                if result.get('NextRecordIdentifier'):
                    extra_kwargs['StartRecordIdentifier'] = result['NextRecordIdentifier']
                continue
            else:
                break
        return all_rrsets

    def list_zones(self):
        all_zones = []
        extra_kwargs = {}
        while True:
            result = self.client.list_hosted_zones(**extra_kwargs)
            all_zones.extend(result['HostedZones'])
            if result.get('IsTruncated'):
                extra_kwargs = {
                    'Marker': result['NextMarker'],
                }
                continue
            else:
                break
        return all_zones

    def create(self, zone_name, record_name, record_type, values, alias):
        assert record_name.endswith('.')
        assert values is None or alias is None
        assert values or alias
        zone_id = self.get_zone_id_from_name(zone_name)
        new_rrs = {
            'Name': record_name,
            'Type': record_type,
        }
        if values:
            assert all(isinstance(v, str) for v in values)
            new_rrs['ResourceRecords'] = [{'Value': v} for v in values]
            new_rrs['TTL'] = 1800
        if alias:
            assert isinstance(alias, str)
            new_rrs['AliasTarget'] = {
                'DNSName': alias,
            }
        chb = {
            'Comment': 'r53sync {dt}'.format(dt=datetime.utcnow()),
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': new_rrs,
                },
            ],
        }
        print('Sending change batch:', chb)
        self.client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch=chb)


def print_zone_table(zones):
    print('  name                                count id                          comment')
    print('  ----------------------------------- ----- --------------------------- ---------------------------------')
    for z in zones:
        comment = z['Config'].get('Comment', '-')
        print('  {:35} {:5} {:27} {}'.format(z['Name'], z['ResourceRecordSetCount'], z['Id'], comment))


def print_rrset_table(rrsets):
    print('  Name                                Type     TTL Info')
    print('  ----------------------------------- ----- ------ ------------------------------------------------------')
    for rrs in rrsets:
        info = []
        if rrs.get('AliasTarget'):
            info.append('alias: {}'.format(rrs['AliasTarget']['DNSName']))
        if rrs.get('ResourceRecords'):
            assert isinstance(rrs['ResourceRecords'], list), repr(rrs['ResourceRecords'])
            for rec in rrs['ResourceRecords']:
                if set(rec.keys()) == {'Value'}:
                    info.append(rec['Value'])
                else:
                    info.append(repr(rec))

        print('  {:35} {:5} {:>6} {}'.format(rrs['Name'], rrs['Type'], rrs.get('TTL', '-'), ', '.join(info)))


def dump_rrsets(zone_name, rrsets):
    out = []
    for rrs in rrsets:
        if rrs['Type'] in ('NS', 'SOA'):
            continue
        data = {
            'name': rrs['Name'],
            'type': rrs['Type'],
        }
        if rrs.get('TTL'):
            data['ttl'] = rrs['TTL']
        if rrs.get('AliasTarget'):
            data['alias'] = rrs['AliasTarget']['DNSName']
        if rrs.get('ResourceRecords'):
            data['values'] = []
            for rec in rrs['ResourceRecords']:
                data['values'].append(rec['Value'])
        out.append(data)
    return {'zone': zone_name, 'rrsets': out}


def print_diff(file_data, current_rrsets):
    current_rrsets = [rrs for rrs in current_rrsets if rrs['Type'] not in ('NS', 'SOA')]
    file_rrsets = file_data['rrsets']
    both, extra_file, extra_current = match_lists(
        file_rrsets, lambda rrs: (rrs['name'].lower(), rrs['type'].upper()),
        current_rrsets, lambda rrs: (rrs['Name'].lower(), rrs['Type'].upper()))
    for file_item, current_item in both:
        assert file_item['name'] == current_item['Name']
        assert file_item['type'] == current_item['Type']
    for file_item in extra_file:
        print('New record in file: {}'.format(file_item))


def sync_records(r53, file_data, current_rrsets):
    current_rrsets = [rrs for rrs in current_rrsets if rrs['Type'] not in ('NS', 'SOA')]
    file_rrsets = file_data['rrsets']
    both, extra_file, extra_current = match_lists(
        file_rrsets, lambda rrs: (rrs['name'].lower(), rrs['type'].upper()),
        current_rrsets, lambda rrs: (rrs['Name'].lower(), rrs['Type'].upper()))
    for file_item, current_item in both:
        assert file_item['name'] == current_item['Name']
        assert file_item['type'] == current_item['Type']
    for file_item in extra_file:
        print('')
        print('{}'.format(file_item))
        do_create = None
        while True:
            response = input('Create? (y/n) > ')
            if response == 'y':
                do_create = True
                break
            if response == 'n':
                do_create = False
                break
            print('Please enter "y" or "n" or quit with Ctrl-C')
        if do_create:
            print('Creating {}'.format(file_item))
            r53.create(
                zone_name=file_data['zone'], record_name=file_item['name'], record_type=file_item['type'],
                values=file_item.get('values'), alias=file_item.get('alias'))



def match_lists(a_items, a_key_f, b_items, b_key_f):
    both, extra_a, extra_b = [], [], []
    a_items_by_key = {}
    for a_item in a_items:
        key = a_key_f(a_item)
        if key in a_items_by_key:
            raise Exception('Duplicate key {!r} in a_items'.format(key))
        a_items_by_key[key] = a_item
    b_keys = set()
    for b_item in b_items:
        key = b_key_f(b_item)
        if key in b_keys:
            raise Exception('Duplicate key {!r} in b_items'.format(key))
        b_keys.add(key)
        if key in a_items_by_key:
            both.append((a_items_by_key[key], b_item))
        else:
            extra_b.append(b_item)
    for a_key, a_item in a_items_by_key.items():
        if a_key not in b_keys:
            extra_a.append(a_item)
    return (both, extra_a, extra_b)



if __name__ == '__main__':
    main()
