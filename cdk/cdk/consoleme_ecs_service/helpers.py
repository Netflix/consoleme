"""
Helpers library for various actions
"""

import os
import subprocess
from pathlib import Path

from aws_cdk import aws_lambda as lambda_


def create_dependencies_layer(self, function_name: str) -> lambda_.LayerVersion:
    base_path = f"./resources/{function_name}"
    output_dir = f"{base_path}/build/{function_name}"
    if not os.environ.get("SKIP_PIP"):
        build_folder = Path(f"{base_path}/build")
        requirements_file = Path(f"{base_path}/requirements.txt")
        # Remove build folder from previous runs
        if build_folder.is_dir():
            subprocess.check_call(f"rm -rf {base_path}/build".split())
        # Remove requirements file from previous runs
        if requirements_file.is_file():
            subprocess.check_call(f"rm -rf {base_path}/requirements.txt".split())
        # Create requirements file using pipreqs
        subprocess.check_call(f"pipreqs {base_path}".split())
        requirements_file = Path(f"{base_path}/requirements.txt")
        if requirements_file.is_file():
            subprocess.check_call(
                f"pip install -r {base_path}/requirements.txt -t {output_dir}/python".split()
            )
    layer_id = f"{function_name}-dependencies"
    layer_code = lambda_.Code.from_asset(output_dir)
    return lambda_.LayerVersion(self, layer_id, code=layer_code)
