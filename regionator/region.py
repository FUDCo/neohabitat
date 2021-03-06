import json
import os
import uuid

from json import JSONEncoder

import parser
import yaml


DEFAULT_REGIONATOR_NAME = '{0} - Generated by Regionator'

ORIENTATION_TO_ID = {
  'FACE_WEST': 0,
  'FACE_NORTH': 1,
  'FACE_EAST': 2,
  'FACE_SOUTH': 3,
}


def _default(self, obj):
  return getattr(obj.__class__, "to_json", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default


MOD_INDEX = {}
with open('./mod_index.yml', 'r') as mod_index:
  MOD_INDEX = yaml.load(mod_index)


class Mod(object):
  def __init__(self, region, identifier, params={}, additional_params={},
      contained_mods=[], parent=None):
    self.region = region
    self.identifier = identifier
    self.params = params
    self.additional_params = additional_params
    self.contained_mods = contained_mods
    self.id = str(uuid.uuid4())[:4]
    self.parent = parent
    for contained_mod in self.contained_mods:
      contained_mod.parent = self

  def __repr__(self):
    return '<Mod(identifier="{0}", params={1})>'.format(self.identifier, self.params)

  @property
  def neohabitat_mod(self):
    mod_json = {
      'type': self.neohabitat_name,
      'x': int(self.params['x']),
      'y': int(self.params['y']),
      'orientation': int(self.params['or']),
    }
    if 'style' in self.params:
      mod_json['style'] = int(self.params['style'])
    if 'gr_state' in self.params:
      mod_json['gr_state'] = int(self.params['gr_state'])

    # Handles the conversion of numerical mod parameters to their respective Neohabitat
    # Mod fields.
    if self.additional_params and self.neohabitat_name in MOD_INDEX:
      chomp_start_key = 8
      translator = MOD_INDEX[self.neohabitat_name]
      for index, mod_key in translator.items():
        if str(index) != 'CHOMP':
          if str(index) in self.additional_params:
            mod_json[mod_key] = self.additional_params[str(index)]
          chomp_start_key += 1
      # If a CHOMP key has been specified, chomps all remaining additional params into
      # the specified field.
      if 'CHOMP' in translator:
        chomp_key = translator['CHOMP']
        mod_json[chomp_key] = self._chomped_params(chomp_start_key)

    return mod_json

  @property
  def neohabitat_name(self):
    return self.identifier.capitalize()

  @property
  def neohabitat_ref(self):
    return 'item-{0}.{1}.{2}'.format(self.identifier, self.id,
        self.region.name.replace('-', '.'))

  def _chomped_params(self, start_index=8):
    params_with_numeric_keys = {
      int(param[0]): param[1] for param in self.additional_params.items()
    }
    ascii_list = []
    for param_key in sorted(params_with_numeric_keys.keys()):
      if param_key >= start_index:
        ascii_list.append(int(params_with_numeric_keys[param_key]))
    return ascii_list

  def to_json(self):
    json_mod = {
      'type': 'item',
      'ref': self.neohabitat_ref,
      'name': self.neohabitat_name,
      'mods': [self.neohabitat_mod],
    }
    if self.parent is not None:
      json_mod['in'] = self.parent.neohabitat_ref
    else:
      json_mod['in'] = self.region.neohabitat_context

    return json_mod


class Region(object):
  def __init__(self, name, params=None, mods=None, parse_results=None):
    self.name = name
    
    if params is None:
      self.params = {}
    else:
      self.params = params
    
    if mods is None:
      self.mods = []
    else:
      self.mods = mods

    if parse_results is not None:
      # It's much easier to work with the pure Python representation of a
      # pyparsing.ParseResults, hence this horrible hack.
      exec('self.raw_results = ' + parse_results.__repr__())
      self.results_dict = self.raw_results[1]

  def __repr__(self):
    return '<Region(name="{0}", params={1}, mods={2})>'.format(self.name, self.params,
        self.mods)

  @classmethod
  def from_rdl_file(cls, rdl_file):
    # For now, we'll assume a 1-to-1 mapping between the region file name and the name
    # of the region
    region_name = os.path.basename(rdl_file.split('.')[-2])
    with open(rdl_file, 'r') as rdlfile:
      rdlfile_text = rdlfile.read()
      results = parser.region.parseString(rdlfile_text)
      return cls.from_parse_results(region_name, results)

  @classmethod
  def from_parse_results(cls, name, parse_results):
    region = cls(name=name, parse_results=parse_results)
    region._parse_params_from_results()
    region._parse_mods_from_results()
    return region

  @property
  def neohabitat_context(self):
    return 'context-{0}'.format(self.name)

  def _parse_params_from_results(self):
    self.params = self._parse_params(self.results_dict['region_params'][0][0])

  def _parse_params(self, param_tokens):
    params = {}
    param_name = None
    param_value = None
    on_name = True
    for token in param_tokens:
      if token == '\n':
        pass
      elif ':' in token:
        on_name = False
      elif token == ';':
        params[param_name] = param_value
        on_name = True
      elif on_name:
        param_name = token
      else:
        param_value = token
    return params

  def _parse_mods_from_results(self):
    mods = self.results_dict['mods']
    for mod in mods[0][1]['mod']:
      mod_dict = mod[1]
      mod_identifier = mod_dict['mod_identifier'][0]

      mod_params = {}
      if 'mod_params' in mod_dict:
        mod_params.update(self._parse_params(mod_dict['mod_params'][0][0]))

      mod_params_additional = {}
      if 'mod_params_additional' in mod_dict:
        mod_params_additional.update(
            self._parse_params(mod_dict['mod_params_additional'][0][0]))

      # Handles the parsing of contained mods using the power of Hack Mode 7.
      contained_mods = []
      if 'inner_mod_1' in mod_dict:
        for inner_mod_1 in mod_dict['inner_mod_1']:
          inner_mod_1_dict = inner_mod_1[1]
          inner_mod_1_identifier = mod_dict['inner_mod_1_identifier'][0]

          inner_mod_1_params = {}
          if 'inner_mod_1_params' in inner_mod_1_dict:
            inner_mod_1_params.update(
                self._parse_params(inner_mod_1_dict['inner_mod_1_params'][0][0]))

          inner_mod_1_params_additional = {}
          if 'inner_mod_1_params_additional' in inner_mod_1_dict:
            inner_mod_1_params_additional.update(
                self._parse_params(inner_mod_1_dict['inner_mod_1_params_additional'][0][0]))

          inner_mod_1_contained_mods = []
          if 'inner_mod_2' in mod_dict:
            for inner_mod_2 in mod_dict['inner_mod_2']:
              inner_mod_2_dict = inner_mod_2[1]
              inner_mod_2_identifier = mod_dict['inner_mod_2_identifier'][0]

              inner_mod_2_params = {}
              if 'inner_mod_2_params' in inner_mod_2_dict:
                inner_mod_2_params.update(
                    self._parse_params(inner_mod_2_dict['inner_mod_2_params'][0][0]))

              inner_mod_2_params_additional = {}
              if 'inner_mod_2_params_additional' in inner_mod_2_dict:
                inner_mod_2_params_additional.update(
                    self._parse_params(inner_mod_2_dict['inner_mod_2_params_additional'][0][0]))         
              
              inner_mod_2_contained_mods = []
              if 'inner_mod_3' in mod_dict:
                for inner_mod_3 in mod_dict['inner_mod_3']:
                  inner_mod_3_dict = inner_mod_3[1]
                  inner_mod_3_identifier = mod_dict['inner_mod_3_identifier'][0]

                  inner_mod_3_params = {}
                  if 'inner_mod_3_params' in inner_mod_3_dict:
                    inner_mod_3_params.update(
                        self._parse_params(inner_mod_3_dict['inner_mod_3_params'][0][0]))

                  inner_mod_3_params_additional = {}
                  if 'inner_mod_3_params_additional' in inner_mod_3_dict:
                    inner_mod_3_params_additional.update(
                        self._parse_params(inner_mod_3_dict['inner_mod_3_params_additional'][0][0]))                  

                  inner_mod_2_contained_mods.append(
                      Mod(region=self, identifier=inner_mod_3_identifier,
                          params=inner_mod_3_params,
                          additional_params=inner_mod_3_params_additional))

              inner_mod_1_contained_mods.append(
                  Mod(region=self, identifier=inner_mod_2_identifier,
                      params=inner_mod_2_params,
                      additional_params=inner_mod_2_params_additional,
                      contained_mods=inner_mod_2_contained_mods))

          contained_mods.append(
              Mod(region=self, identifier=inner_mod_1_identifier,
                  params=inner_mod_1_params,
                  additional_params=inner_mod_1_params_additional,
                  contained_mods=inner_mod_1_contained_mods))

      self.mods.append(Mod(region=self, identifier=mod_identifier, params=mod_params,
          additional_params=mod_params_additional, contained_mods=contained_mods))

  def to_json(self):
    region_mod = {
      'town_dir': '',
      'port_dir': '',
      'type': 'Region',
      'nitty_bits': 3,
      'neighbors': ['', '', '', ''],
    }
    if 'north' in self.params:
      region_mod['neighbors'][0] = 'context-{0}'.format(
          self.params['north'].split('.')[0])
    if 'east' in self.params:
      region_mod['neighbors'][1] = 'context-{0}'.format(
          self.params['east'].split('.')[0])
    if 'south' in self.params:
      region_mod['neighbors'][2] = 'context-{0}'.format(
          self.params['south'].split('.')[0])
    if 'west' in self.params:
      region_mod['neighbors'][3] = 'context-{0}'.format(
          self.params['west'].split('.')[0])
    if 'region_orientation' in self.params and self.params['region_orientation'] in ORIENTATION_TO_ID:
      region_mod['orientation'] = ORIENTATION_TO_ID[self.params['region_orientation']]

    region_context = {
      'type': 'context',
      'ref': self.neohabitat_context,
      'capacity': 6,
      'name': DEFAULT_REGIONATOR_NAME.format(self.name),
      'mods': [region_mod]
    }

    region_contents = [region_context]

    # Performs a depth-first search through the containership tree of all mods.
    def _dfs_mods(cur_mods):
      for mod in cur_mods:
        _dfs_mods(mod.contained_mods)
        region_contents.append(mod)

    _dfs_mods(self.mods)

    return region_contents
