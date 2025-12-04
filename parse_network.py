#!/usr/bin/env python3
"""
parse_network.py

Resolve LZA network-config.yaml by applying values from replacements-config.yaml,
then output a JSON file with:
  - resolved_network_config: the fully-resolved raw config
  - graph: a normalized network graph (VPCs, subnets, TGWs, etc.)

Usage (from your project folder):

    python parse_network.py --network network-config.yaml \
                            --replacements replacements-config.yaml \
                            --out network-graph.json
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_yaml(path: Path):
    """Load a YAML file and return the parsed Python object."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_replacements(replacements_raw: dict) -> dict:
    """
    Turn your replacements-config.yaml into a simple dict:
      {
        "AcceleratorPrefix": "AWSAccelerator",
        "AcceleratorHomeRegion": "ca-central-1",
        "VpcEndpointCidr": "10.235.0.0/22",
        "SandboxAllowedRegions": ["ca-central-1", "us-east-1", ...],
        ...
      }

    Expects a structure like:
      globalReplacements:
        - key: ...
          type: String | StringList
          value: ...
    """
    if not isinstance(replacements_raw, dict):
        return {}

    items = replacements_raw.get("globalReplacements", [])
    if not isinstance(items, list):
        return {}

    mapping = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        key = item.get("key")
        type_ = item.get("type", "String")
        value = item.get("value")

        if key is None:
            continue

        if type_ == "StringList":
            # Ensure value is stored as a list
            if not isinstance(value, list):
                value = [value] if value is not None else []
            mapping[str(key)] = value
        else:
            # Everything else is stored as a simple string
            mapping[str(key)] = "" if value is None else str(value)

    return mapping


def render_network_config(network_path: Path, replacements: dict) -> dict:
    """
    Read network-config.yaml as raw text, replace {{ Key }} / {{Key}} / ${Key}
    using the replacements map, then parse the rendered YAML.

    This avoids PyYAML choking on un-rendered Jinja-style {{ variables }}.
    """
    raw_text = network_path.read_text(encoding="utf-8")

    for key, value in replacements.items():
        if isinstance(value, list):
            replacement_str = ",".join(str(v) for v in value)
        else:
            replacement_str = str(value)

        # Handle Jinja-style with/without spaces:
        #   {{ AcceleratorHomeRegion }}  or  {{AcceleratorHomeRegion}}
        raw_text = raw_text.replace(f"{{{{ {key} }}}}", replacement_str)
        raw_text = raw_text.replace(f"{{{{{key}}}}}", replacement_str)

        # Handle ${Key} style
        raw_text = raw_text.replace(f"${{{key}}}", replacement_str)

    # Now the text should no longer contain bare {{ ... }} placeholders
    # Safe to parse as YAML
    return yaml.safe_load(raw_text)


def extract_network_graph(network_cfg: dict) -> dict:
    """
    Build a normalized network graph structure from the resolved network config.

    This is designed to be resilient to minor schema differences, but assumes
    LZA-style keys:
      - transitGateways
      - vpcs (each with subnets and transitGatewayAttachments)
      - customerGateways (for VPN)
      - directConnectGateways
    """

    # ---- Transit Gateways ----
    transit_gateways = []
    for tgw in network_cfg.get("transitGateways", []):
        if not isinstance(tgw, dict):
            continue
        tgw_id = tgw.get("name")
        transit_gateways.append(
            {
                "id": tgw_id,
                "name": tgw.get("name"),
                "account": tgw.get("account"),
                "region": tgw.get("region"),
                "asn": tgw.get("asn"),
            }
        )

    # ---- VPCs & Subnets ----
    vpcs = []
    tgw_attachments = []

    for vpc in network_cfg.get("vpcs", []):
        if not isinstance(vpc, dict):
            continue

        vpc_id = vpc.get("name")
        account = vpc.get("account", "unknown")
        region = vpc.get("region", network_cfg.get("region", None))
        # Handle both single CIDR and CIDR array
        cidrs = vpc.get("cidrs", [])
        if cidrs and isinstance(cidrs, list):
            cidr = cidrs[0]  # Use first CIDR
        else:
            cidr = vpc.get("cidr") or vpc.get("ipv4CidrBlock") or vpc.get("ipv4Cidr")

        # Subnets
        subnets = []
        for subnet in vpc.get("subnets", []):
            if not isinstance(subnet, dict):
                continue
            subnet_name = subnet.get("name")
            subnet_id = f"{vpc_id}-{subnet_name}" if vpc_id and subnet_name else subnet_name

            subnet_cidr = (
                subnet.get("cidr")
                or subnet.get("ipv4CidrBlock")
                or subnet.get("ipv4Cidr")
            )
            az = subnet.get("availabilityZone") or subnet.get("az")
            subnet_type = (
                subnet.get("type")
                or subnet.get("subnetType")
                or subnet.get("tier")
                or "unknown"
            )

            subnets.append(
                {
                    "id": subnet_id,
                    "name": subnet_name,
                    "cidr": subnet_cidr,
                    "az": az,
                    "type": subnet_type,
                }
            )

        vpcs.append(
            {
                "id": vpc_id,
                "name": vpc.get("name"),
                "account": account,
                "region": region,
                "cidr": cidr,
                "azs": sorted({s["az"] for s in subnets if s.get("az")}),
                "subnets": subnets,
            }
        )

        # TGW Attachments for this VPC
        for attachment in vpc.get("transitGatewayAttachments", []):
            if not isinstance(attachment, dict):
                continue

            tgw_ref = attachment.get("transitGateway")
            if isinstance(tgw_ref, dict):
                tgw_name = tgw_ref.get("name")
            else:
                tgw_name = tgw_ref
            att_name = attachment.get("name") or f"{vpc_id}-{tgw_name}"
            subnet_names = attachment.get("subnets", [])

            # Map subnet names in the attachment to our constructed subnet IDs
            attachment_subnet_ids = [
                f"{vpc_id}-{sn}" if vpc_id and sn else sn for sn in subnet_names
            ]

            tgw_attachments.append(
                {
                    "id": f"{vpc_id}-{tgw_name}" if vpc_id and tgw_name else att_name,
                    "tgw_id": tgw_name,
                    "vpc_id": vpc_id,
                    "name": att_name,
                    "subnets": attachment_subnet_ids,
                    "route_tables": {
                        "tgw_association": attachment.get("routeTableAssociations"),
                        "tgw_propagations": attachment.get(
                            "routeTablePropagations", []
                        ),
                    },
                }
            )

    # ---- Direct Connect Gateways ----
    dx_gateways = []
    for dxgw in network_cfg.get("directConnectGateways", []):
        if not isinstance(dxgw, dict):
            continue

        dxgw_name = dxgw.get("name")
        dx_entry = {
            "id": dxgw_name,
            "name": dxgw_name,
            "account": dxgw.get("account"),
            "asn": dxgw.get("asn"),
            "virtual_interfaces": [],
            "tgw_associations": [],
        }

        for vif in dxgw.get("virtualInterfaces", []):
            if not isinstance(vif, dict):
                continue
            dx_entry["virtual_interfaces"].append(
                {
                    "id": vif.get("name"),
                    "name": vif.get("name"),
                    "connection_id": vif.get("connectionId"),
                    "customer_asn": vif.get("customerAsn"),
                    "region": vif.get("region"),
                    "type": vif.get("type"),
                    "vlan": vif.get("vlan"),
                    "jumbo_frames": vif.get("jumboFrames"),
                }
            )

        for assoc in dxgw.get("transitGatewayAssociations", []):
            if not isinstance(assoc, dict):
                continue
            dx_entry["tgw_associations"].append(
                {
                    "tgw_name": assoc.get("name"),
                    "account": assoc.get("account"),
                    "allowed_prefixes": assoc.get("allowedPrefixes", []),
                    "route_table_associations": assoc.get("routeTableAssociations", []),
                    "route_table_propagations": assoc.get(
                        "routeTablePropagations", []
                    ),
                }
            )

        dx_gateways.append(dx_entry)

    # ---- VPN Connections via Customer Gateways ----
    vpn_connections = []
    for cgw in network_cfg.get("customerGateways", []):
        if not isinstance(cgw, dict):
            continue

        cgw_name = cgw.get("name")
        for vpn in cgw.get("vpnConnections", []):
            if not isinstance(vpn, dict):
                continue
            vpn_connections.append(
                {
                    "name": vpn.get("name"),
                    "customer_gateway": cgw_name,
                    "account": cgw.get("account"),
                    "region": cgw.get("region"),
                    "transit_gateway": vpn.get("transitGateway"),
                    "static_routes_only": vpn.get("staticRoutesOnly"),
                    "route_table_associations": vpn.get("routeTableAssociations", []),
                    "route_table_propagations": vpn.get("routeTablePropagations", []),
                    "tunnel_specifications": vpn.get("tunnelSpecifications", []),
                }
            )

    # ---- CNFGW Endpoints ----
    cnfgw_endpoints = []
    if network_cfg.get("transitGateways"):
        for tgw in network_cfg.get("transitGateways", []):
            if not isinstance(tgw, dict):
                continue
            for rt in tgw.get("routeTables", []):
                if not isinstance(rt, dict):
                    continue
                for route in rt.get("routes", []):
                    if not isinstance(route, dict):
                        continue
                    target_endpoint = route.get("targetVpcEndpoint")
                    if target_endpoint and "cnfgw" in target_endpoint.lower():
                        cnfgw_endpoints.append({
                            "id": target_endpoint,
                            "name": target_endpoint,
                            "tgw": tgw.get("name"),
                            "route_table": rt.get("name"),
                            "destination": route.get("destinationCidrBlock") or route.get("destination"),
                            "type": "palo_alto_cnfgw"
                        })

    graph = {
        "transit_gateways": transit_gateways,
        "vpcs": vpcs,
        "tgw_attachments": tgw_attachments,
        "dx_gateways": dx_gateways,
        "vpn_connections": vpn_connections,
        "cnfgw_endpoints": cnfgw_endpoints,
    }

    return graph


def main():
    parser = argparse.ArgumentParser(
        description="Resolve LZA network-config.yaml with replacements-config.yaml"
    )
    parser.add_argument(
        "--network",
        required=True,
        type=Path,
        help="Path to network-config.yaml",
    )
    parser.add_argument(
        "--replacements",
        required=True,
        type=Path,
        help="Path to replacements-config.yaml",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output JSON file (resolved config / graph)",
    )
    args = parser.parse_args()

    # 1) Load replacements-config.yaml and build the key->value map
    replacements_raw = load_yaml(args.replacements)
    repl_map = build_replacements(replacements_raw)

    # 2) Render network-config.yaml as text with replacements applied, then parse YAML
    network_resolved = render_network_config(args.network, repl_map)

    # 3) Build the network graph from the resolved config
    graph = extract_network_graph(network_resolved)

    # 4) Build final output
    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "graph": graph,
        "resolved_network_config": network_resolved,
    }

    # 5) Write JSON output
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote resolved network graph to {args.out}")


if __name__ == "__main__":
    main()
