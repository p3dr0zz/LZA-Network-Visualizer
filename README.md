# LZA Network Visualizer

A comprehensive network visualization and analysis tool for AWS Landing Zone Accelerator (LZA) configurations. This tool helps you understand, document, and validate your LZA network architecture through interactive visualizations and detailed analysis.

## 🌟 Features

- **Interactive Network Diagram**: Visual representation of your LZA network topology
- **Comprehensive Overview**: Wiki-style documentation generated from your configuration
- **Network Verification**: Automated checks for CIDR overlaps, connectivity, and CCCS compliance
- **Traffic Flow Analysis**: Visualize data flow paths between network components
- **CCCS Medium Support**: Built specifically for CCCS Medium security patterns
- **Palo Alto CNFGW Detection**: Automatic detection and visualization of firewall endpoints

## 📋 Prerequisites

- **Python 3.7+** (required to run the configuration parser)
- Modern web browser (for the visualizer interface)

## 🚀 Quick Start

### 0. Setup Python Environment (Optional but Recommended)

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install pyyaml
```

### 1. Generate Network Data

First, parse your LZA configuration files to generate the network data:

```bash
python parse_network.py --network network-config.yaml --replacements replacements-config.yaml --out network-graph.json
```

**Parameters:**
- `--network`: Path to your LZA network-config.yaml file
- `--replacements`: Path to your replacements-config.yaml file  
- `--out`: Output JSON file name

### 2. Launch the Visualizer

Start a local web server to run the visualizer:

```bash
python -m http.server 8000
```

Then open your browser to: `http://localhost:8000`

### 3. Load Your Data

1. Click "Choose File" in the visualizer
2. Select your generated `network-graph.json` file
3. Explore the different tabs:
   - **Network Diagram**: Interactive topology visualization
   - **Overview**: Comprehensive network documentation
   - **Verification**: Automated compliance and connectivity checks
   - **Visual Flow**: Traffic flow analysis between components

## 📁 Sample Files

This repository includes CCCS reference sample files to help you get started:

- `sample-network-config.yaml` - Example LZA network configuration
- `sample-replacements-config.yaml` - Example template replacements
- `sample-network-graph.json` - Pre-generated sample output

You can use these samples to test the visualizer before using your own configuration files.

## 🏗️ Architecture Support

### CCCS Medium Patterns
- Hub-and-spoke architecture with Transit Gateway
- Account-based workload isolation
- Perimeter security controls
- Multi-AZ high availability
- Network segmentation and CIDR management

### Supported Components
- **VPCs**: Perimeter, Endpoint, Central, and Workload VPCs
- **Transit Gateway**: Route tables, attachments, and routing
- **Hybrid Connectivity**: Direct Connect and VPN connections
- **Security**: Palo Alto CNFGW, Security Groups, NACLs
- **Subnets**: Intelligent type detection and documentation

## 🔍 What Gets Analyzed

### Network Verification
- CIDR overlap detection
- Transit Gateway connectivity validation
- Multi-AZ deployment checks
- Security group and NACL analysis
- CCCS Medium compliance verification
- Resource limit warnings

### Traffic Flow Analysis
- North-South traffic (Internet ↔ Applications)
- East-West traffic (Inter-VPC communication)
- Hybrid connectivity (On-premises ↔ AWS)
- Security inspection points
- Route table analysis

## 📊 Visualization Features

### Interactive Network Diagram
- **Hierarchical Layout**: TGW at top, VPCs in organized rows
- **Color-coded Components**: Different colors for different VPC types
- **Dynamic Positioning**: Subnets organized by availability zone
- **Clickable Elements**: Detailed information on selection
- **Export Options**: PNG and SVG export capabilities

### Comprehensive Documentation
- **Live Data**: Always up-to-date with your configuration
- **CIDR Tables**: Detailed subnet breakdowns with intelligent type detection
- **Traffic Flow Examples**: Step-by-step packet flow explanations
- **Architecture Explanations**: Plain English descriptions of network design

## 🛠️ Configuration Files

### network-config.yaml
Your main LZA network configuration file containing:
- VPC definitions and CIDR blocks
- Subnet configurations
- Transit Gateway settings
- Route table definitions
- Security group and NACL rules
- Hybrid connectivity settings

### replacements-config.yaml
Template replacement values for your network configuration:
- Region settings
- Account IDs
- Naming prefixes
- Environment-specific values

The parser resolves all `{{ variable }}` templates in your network configuration using the replacement values.

## 🎯 Use Cases

- **Network Documentation**: Generate always-current network architecture docs
- **Design Validation**: Verify network design before deployment
- **Compliance Checking**: Ensure CCCS Medium pattern compliance
- **Troubleshooting**: Visualize traffic flows and connectivity
- **Team Onboarding**: Help new team members understand the network
- **Change Management**: Visualize impact of network changes

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🔗 Repository

This project is hosted at: https://github.com/p3dr0zz/LZA-Network-Visualizer

## 🙏 Acknowledgments

- Built for AWS Landing Zone Accelerator (LZA) configurations
- Designed to support CCCS Medium security patterns
- Inspired by the need for better network visualization and documentation tools
