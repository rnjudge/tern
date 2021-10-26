# Copyright (c) 2021 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

"""
OpossumUI Generator document
"""

import json
import logging

from typing import Any, Dict, List

from tern.formats.spdx import spdx_common
from tern.utils.general import get_git_rev_or_version
from tern.utils import constants
from tern.formats import generator
from tern.report import content


# global logger
logger = logging.getLogger(constants.logger_name)


def _calculate_file_tree_from_paths(resources: List[str]) -> Dict[str, Any]:
    filetree: Dict[str, Any] = {}

    for resource in resources:
        if resource != "/":
            path_elements: List[str] = list(filter(None, resource.split("/")))

            _add_resource_to_tree(
                target_filetree=filetree,
                path_elements=path_elements,
                is_file=resource[-1] == "/"
            )
    return filetree


def _add_resource_to_tree(
    target_filetree: Dict[
        str, Any
    ],
    path_elements: List[str],
    is_file: bool,
) -> None:
    element_max_index = len(path_elements) - 1

    for index, path_element in enumerate(path_elements):
        if target_filetree.get(path_element) is None:
            target_filetree[path_element] = (
                1 if (index == element_max_index) and is_file else {}
            )
        target_filetree = target_filetree[path_element]


def get_external_attrs(image_obj):
    '''Create a dict which contains attribution information about a file or
    folder. The key is the uuid of the package and the value is a dictionary
    of metadata'''
    external_attrs = {}
    resources_to_attrs = {}
    attr_breakpoints = set()
    for layer in image_obj.layers:
        layer_uuid = spdx_common.get_uuid()

        layer_path = f"/{'%03d' % layer.layer_index}"
        
        if f"{pkg_path}/" in resources_to_attrs.keys():
            resources_to_attrs[f"{pkg_path}/"].append(layer_uuid)
        else:
            resources_to_attrs[f"{pkg_path}/"] = [layer_uuid]

        external_attrs[layer_uuid] = {
            "source": {
                "name": "Tern:Layer",
                "documentConfidence": int(70.0)
            },
            "comment": str(layer) # TODO: should be the command that generated the layer
        }

        for pkg in layer.packages:
            pkg_uuid = spdx_common.get_uuid()

            pkg_path = f"{layer_path}/Packages/{pkg.source}/{pkg.name}/"
            attr_breakpoints.add(f"{layer_path}/Packages/{pkg.source}/")
            attr_breakpoints.add(f"{layer_path}/Packages/")

            if pkg_path in resources_to_attrs.keys():
                resources_to_attrs[pkg_path].append(pkg_uuid)
            else:
                resources_to_attrs[pkg_path] = [pkg_uuid]

            for file_in_pkg in pkg.files:
                absolute_file_in_pkg = f"{layer_path}/{file_in_pkg}"
                if absolute_file_in_pkg in resources_to_attrs.keys():
                    resources_to_attrs[absolute_file_in_pkg].append(pkg_uuid)
                else:
                    resources_to_attrs[absolute_file_in_pkg] = [pkg_uuid]

            pkg_comment = ''
            if pkg.origins.origins:
                for notice_origin in pkg.origins.origins:
                    pkg_comment = pkg_comment + content.print_notices(
                        notice_origin, '', '\t')
            # Debian will have a pkg_licenses value but not license
            pkg_license = pkg.pkg_license if pkg.pkg_license else \
                ''.join(pkg.pkg_licenses)
            external_attrs[pkg_uuid] = {
                "source": {
                    "name": f"Tern:{pkg.source}",
                    "documentConfidence": int(70.0)
                },
                "comment": pkg_comment,
                "packageName": pkg.name,
                "packageVersion": pkg.version if pkg.version else "NONE",
                "url": pkg.proj_url,
                "licenseName": pkg_license if pkg_license else "NONE",
                "copyright": pkg.copyright if pkg.copyright else "NONE"
            }
    return external_attrs, resources_to_attrs, attr_breakpoints


def get_document_dict(image_obj):
    '''Return a dictionary that maps the following fields:
        metadata: containers project-level information
        resources: defines the file tree
        externalAttributions: contains attributions provided as signals
        resourcesToAttributions: links attributions to file paths
        attributionBreakpoints: Folders where the attribution inference stops.
        '''
    docu_dict = {
        "metadata": {
            "projectId": get_git_rev_or_version()[1],
            "projectTitle": "Tern report for {}".format(image_obj.name),
            "fileCreationDate": spdx_common.get_timestamp()
        }
    }

    docu_dict["externalAttributions"], docu_dict["resourcesToAttributions"], docu_dict["attributionBreakpoints"] = get_external_attrs(image_obj)
    docu_dict["resources"] = _calculate_file_tree_from_paths(list(docu_dict["resourcesToAttributions"].keys()).append(docu_dict["attributionBreakpoints"]))
    return docu_dict


class OpossumUI(generator.Generate):
    def generate(self, image_obj_list, print_inclusive=False):
        logger.debug("Generating OpossumUI document...")
        image_obj = image_obj_list[0]
        report = get_document_dict(image_obj)
        return json.dumps(report)
