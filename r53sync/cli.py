#!/usr/bin/env python3

import argparse
import click
from datetime import datetime
import logging
from pprint import pprint
import yaml

from .r53sync import R53Sync

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.pass_context
def main(ctx, verbose):
    ctx.obj = R53Sync()
    setup_logging(verbose)


@main.command()
@click.pass_context
def zones(ctx):
    ctx.obj.list_zones()


@main.command()
@click.argument('zone_name')
@click.pass_context
def records(ctx, zone_name):
    ctx.obj.list_zone_records(zone_name)

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


def setup_logging(verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s: %(message)s')
        logging.getLogger('botocore').setLevel(logging.INFO)
        logging.getLogger('botocore.vendored.requests').setLevel(logging.WARNING)


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
