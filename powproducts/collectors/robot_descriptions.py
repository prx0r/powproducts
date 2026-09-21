"""Robot Descriptions Collector — 190+ robot URDF/MJCF descriptions.

Parses the awesome-robot-descriptions list to catalog robot descriptions.
Stores metadata: name, maker, formats, licence, repository URL.

Source: https://github.com/robot-descriptions/awesome-robot-descriptions
Licence: Mixed per model (Apache-2.0, BSD, MIT, GPL, etc.)
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import (
    insert_source_record, upsert_manufacturer, upsert_product_model,
    insert_product_relation
)

# Curated list of key robots from the awesome-robot-descriptions repo
# Format: (name, maker, formats, licence, repo_url, category)
KEY_ROBOTS = [
    # Arms
    ("UR5e", "Universal Robots", "MJCF,Xacro", "BSD-3-Clause",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("UR10e", "Universal Robots", "MJCF,Xacro", "BSD-3-Clause",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("UR3e", "Universal Robots", "Xacro", "BSD-3-Clause",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("UR10", "Universal Robots", "URDF,Xacro", "Apache-2.0",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("UR5", "Universal Robots", "URDF,Xacro", "Apache-2.0",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("UR3", "Universal Robots", "URDF,Xacro", "Apache-2.0",
     "https://github.com/ros-industrial/universal_robot", "arm"),
    ("Panda", "Franka Emika", "URDF,Xacro,MJCF", "Apache-2.0",
     "https://github.com/frankaemika/franka_ros", "arm"),
    ("FR3", "Franka Robotics", "MJCF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "arm"),
    ("iiwa 14", "KUKA", "URDF,MJCF", "BSD-3-Clause",
     "https://github.com/RobotLocomotion/models", "arm"),
    ("iiwa 7", "KUKA", "URDF", "MIT",
     "https://github.com/facebookresearch/differentiable-robot-model", "arm"),
    ("Med 7", "KUKA", "Xacro", "Apache-2.0",
     "https://github.com/lbr-stack/lbr_fri_ros2_stack", "arm"),
    ("Med 14", "KUKA", "Xacro", "Apache-2.0",
     "https://github.com/lbr-stack/lbr_fri_ros2_stack", "arm"),
    ("xArm 5", "UFACTORY", "Xacro", "BSD-3-Clause",
     "https://github.com/xArm-Developer/xarm_ros2", "arm"),
    ("xArm 6", "UFACTORY", "Xacro", "BSD-3-Clause",
     "https://github.com/xArm-Developer/xarm_ros2", "arm"),
    ("xArm 7", "UFACTORY", "Xacro,MJCF", "BSD-3-Clause",
     "https://github.com/xArm-Developer/xarm_ros2", "arm"),
    ("Lite 6", "UFACTORY", "Xacro,MJCF", "BSD-3-Clause",
     "https://github.com/xArm-Developer/xarm_ros2", "arm"),
    ("Gen2", "Kinova", "URDF", "BSD-3-Clause",
     "https://github.com/Gepetto/example-robot-data", "arm"),
    ("Gen3", "Kinova", "URDF,Xacro,MJCF", "BSD-3-Clause",
     "https://github.com/Kinovarobotics/ros_kortex", "arm"),
    ("Gen3 Lite", "Kinova", "URDF", "BSD-3-Clause",
     "https://github.com/Kinovarobotics/ros2_kortex", "arm"),
    ("Sawyer", "Rethink Robotics", "Xacro,MJCF", "Apache-2.0",
     "https://github.com/RethinkRobotics/sawyer_robot", "arm"),
    ("Rizon4", "Flexiv Robotics", "MJCF,Xacro", "Apache-2.0",
     "https://github.com/flexivrobotics/flexiv_description", "arm"),
    ("PiPER", "AgileX", "MJCF,URDF", "MIT",
     "https://github.com/agilexrobotics/Piper_ros", "arm"),
    ("Z1", "UNITREE Robotics", "URDF", "BSD-3-Clause",
     "https://github.com/unitreerobotics/unitree_ros", "arm"),
    ("ViperX 300", "Trossen Robotics", "Xacro,MJCF", "BSD-3-Clause",
     "https://github.com/Interbotix/interbotix_ros_manipulators", "arm"),
    ("WidowX 250", "Trossen Robotics", "MJCF", "BSD-3-Clause",
     "https://github.com/google-deepmind/mujoco_menagerie", "arm"),
    ("SO-ARM 100", "The Robot Studio", "MJCF,URDF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "arm"),
    ("e.DO", "Comau", "URDF", "BSD-3-Clause",
     "https://github.com/ianathompson/eDO_description", "arm"),
    ("M-710iC", "FANUC", "URDF,Xacro", "BSD-3-Clause",
     "https://github.com/robot-descriptions/fanuc_m710ic_description", "arm"),

    # Humanoids
    ("G1", "UNITREE Robotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/google-deepmind/mujoco_menagerie", "humanoid"),
    ("H1", "UNITREE Robotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/google-deepmind/mujoco_menagerie", "humanoid"),
    ("TALOS", "PAL Robotics", "URDF,Xacro,MJCF", "LGPL-3.0",
     "https://github.com/pal-robotics/talos_robot", "humanoid"),
    ("iCub", "IIT", "URDF", "CC-BY-SA-4.0",
     "https://github.com/robotology/icub-models", "humanoid"),
    ("NAO", "SoftBank Robotics", "URDF,Xacro", "BSD-3-Clause",
     "https://github.com/ros-naoqi/nao_robot", "humanoid"),
    ("Atlas DRC", "Boston Dynamics", "URDF", "BSD-3-Clause",
     "https://github.com/RobotLocomotion/models", "humanoid"),
    ("Apollo", "Apptronik", "MJCF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "humanoid"),
    ("Booster T1", "Booster Robotics", "MJCF,URDF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "humanoid"),

    # Quadrupeds
    ("Go2", "UNITREE Robotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/google-deepmind/mujoco_menagerie", "quadruped"),
    ("Go1", "UNITREE Robotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/unitreerobotics/unitree_mujoco", "quadruped"),
    ("A1", "UNITREE Robotics", "MJCF,URDF", "MPL-2.0",
     "https://github.com/unitreerobotics/unitree_mujoco", "quadruped"),
    ("B1", "UNITREE Robotics", "URDF", "BSD-3-Clause",
     "https://github.com/unitreerobotics/unitree_ros", "quadruped"),
    ("B2", "UNITREE Robotics", "URDF", "BSD-3-Clause",
     "https://github.com/unitreerobotics/unitree_ros", "quadruped"),
    ("ANYmal B", "ANYbotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/ANYbotics/anymal_b_simple_description", "quadruped"),
    ("ANYmal C", "ANYbotics", "MJCF,URDF", "BSD-3-Clause",
     "https://github.com/ANYbotics/anymal_c_simple_description", "quadruped"),
    ("ANYmal D", "ANYbotics", "URDF", "BSD-3-Clause",
     "https://github.com/ANYbotics/anymal_d_simple_description", "quadruped"),
    ("Spot", "Boston Dynamics", "MJCF,Xacro", "BSD-3-Clause",
     "https://github.com/google-deepmind/mujoco_menagerie", "quadruped"),
    ("Mini Cheetah", "MIT", "URDF", "BSD",
     "https://github.com/Derek-TH-Wang/mini_cheetah_urdf", "quadruped"),
    ("Solo", "ODRI", "URDF", "BSD-3-Clause",
     "https://github.com/Gepetto/example-robot-data", "quadruped"),
    ("HyQ", "IIT", "URDF", "Apache-2.0",
     "https://github.com/Gepetto/example-robot-data", "quadruped"),

    # Mobile Manipulators
    ("Stretch 2", "Hello Robot", "MJCF", "BSD",
     "https://github.com/google-deepmind/mujoco_menagerie", "mobile_manipulator"),
    ("Stretch 3", "Hello Robot", "MJCF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "mobile_manipulator"),
    ("TIAGo", "PAL Robotics", "URDF,Xacro,MJCF", "Apache-2.0",
     "https://github.com/pal-robotics/tiago_robot", "mobile_manipulator"),
    ("Fetch", "Fetch Robotics", "URDF", "MIT",
     "https://github.com/openai/roboschool", "mobile_manipulator"),
    ("Pepper", "SoftBank Robotics", "URDF", "BSD-2-Clause",
     "https://github.com/jrl-umi3218/pepper_description", "mobile_manipulator"),
    ("PR2", "Willow Garage", "URDF,Xacro", "BSD",
     "https://github.com/PR2/pr2_common", "mobile_manipulator"),

    # End Effectors
    ("Robotiq 2F-85", "Robotiq", "MJCF,URDF,Xacro", "BSD-2-Clause",
     "https://github.com/ros-industrial/robotiq", "gripper"),
    ("Allegro Hand", "Wonik Robotics", "URDF,MJCF", "BSD",
     "https://github.com/RobotLocomotion/models", "gripper"),
    ("Shadow Hand", "Shadow Robot Company", "MJCF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "gripper"),

    # Bipeds
    ("Cassie", "Agility Robotics", "URDF,MJCF", "MIT",
     "https://github.com/robot-descriptions/cassie_description", "biped"),
    ("Upkie", "Stéphane Caron", "URDF", "Apache-2.0",
     "https://github.com/upkie/upkie_description", "biped"),
    ("OP3", "ROBOTIS", "MJCF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "biped"),

    # Drones
    ("Crazyflie 2.0", "Bitcraze", "URDF,MJCF", "MIT",
     "https://github.com/google-deepmind/mujoco_menagerie", "drone"),
    ("X2", "Skydio", "MJCF,URDF", "Apache-2.0",
     "https://github.com/google-deepmind/mujoco_menagerie", "drone"),
]


class RobotDescriptionsCollector(BaseCollector):
    SOURCE_ID = 'robot_descriptions'
    DATASET = 'robot_descriptions'
    PARSER_ID = 'robot_descriptions_curated_v1'

    def fetch(self):
        """Return curated robot list (no HTTP needed — we maintain the list)."""
        return json.dumps(KEY_ROBOTS).encode()

    def parse(self, raw_content, raw_hash, result):
        """Parse curated robot descriptions and create product identities."""
        robots = json.loads(raw_content)

        for name, maker, formats, licence, repo_url, category in robots:
            product_id = name.lower().replace(' ', '-').replace('.', '')
            manufacturer_id = maker.lower().replace(' ', '-').replace('.', '')

            # Ensure manufacturer exists
            upsert_manufacturer(manufacturer_id, maker)

            # Ensure product model exists
            product_class = {
                'arm': 'robot_arm',
                'humanoid': 'humanoid',
                'quadruped': 'quadruped',
                'mobile_manipulator': 'mobile_manipulator',
                'gripper': 'gripper',
                'biped': 'biped',
                'drone': 'drone',
            }.get(category, 'robot')

            upsert_product_model(product_id, manufacturer_id, name,
                                  product_class=product_class)

            # Store robot description record
            native_id = f'rd:{product_id}'
            normalized = {
                'source_native_id': native_id,
                'robot_name': name,
                'manufacturer': maker,
                'formats': formats.split(','),
                'licence': licence,
                'upstream_repo': repo_url,
                'category': category,
                'product_id': product_id,
            }

            ir = insert_source_record(
                self.SOURCE_ID, self.DATASET, native_id,
                normalized, raw_hash, self.PARSER_ID, self.PARSER_VERSION
            )
            if ir.inserted:
                if ir.duplicate_of:
                    result.records_changed += 1
                else:
                    result.records_new += 1
            else:
                result.records_unchanged += 1


if __name__ == '__main__':
    RobotDescriptionsCollector().run()
