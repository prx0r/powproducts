"""MuJoCo Menagerie Collector — curated robot models.

Fetches the model list from the MuJoCo Menagerie GitHub repo.
Useful for: robot identity, kinematic structure, joint information.

Source: https://github.com/google-deepmind/mujoco_menagerie
Licence: Mixed per model (Apache-2.0, BSD, MIT, etc.)
"""

import json
from datetime import datetime, timezone
from powproducts.collectors.base import BaseCollector, CollectorResult
from powproducts.shared.persist import (
    insert_source_record, upsert_manufacturer, upsert_product_model
)

# Curated list of MuJoCo Menagerie models
# Format: (model_name, manufacturer, licence, category)
MENAGERIE_MODELS = [
    ("franka_emika_panda", "Franka Emika", "Apache-2.0", "arm"),
    ("franka_fr3", "Franka Robotics", "Apache-2.0", "arm"),
    ("franka_fr3_v2", "Franka Robotics", "Apache-2.0", "arm"),
    ("universal_robots_ur5e", "Universal Robots", "BSD-3-Clause", "arm"),
    ("universal_robots_ur10e", "Universal Robots", "BSD-3-Clause", "arm"),
    ("kuka_iiwa_14", "KUKA", "BSD-3-Clause", "arm"),
    ("ufactory_xarm7", "UFACTORY", "BSD-3-Clause", "arm"),
    ("ufactory_lite6", "UFACTORY", "BSD-3-Clause", "arm"),
    ("flexiv_rizon4", "Flexiv Robotics", "Apache-2.0", "arm"),
    ("rethink_robotics_sawyer", "Rethink Robotics", "Apache-2.0", "arm"),
    ("agilex_piper", "AgileX", "MIT", "arm"),
    ("trs_so_arm100", "The Robot Studio", "Apache-2.0", "arm"),
    ("robotstudio_so101", "The Robot Studio", "Apache-2.0", "arm"),
    ("trossen_vx300s", "Trossen Robotics", "BSD-3-Clause", "arm"),
    ("trossen_wx250s", "Trossen Robotics", "BSD-3-Clause", "arm"),
    ("dynamixel_2r", "ROBOTIS", "MIT", "arm"),
    ("low_cost_robot_arm", "Alexander Koch", "Apache-2.0", "arm"),

    # Humanoids
    ("unitree_g1", "UNITREE Robotics", "BSD-3-Clause", "humanoid"),
    ("unitree_h1", "UNITREE Robotics", "BSD-3-Clause", "humanoid"),
    ("pal_talos", "PAL Robotics", "Apache-2.0", "humanoid"),
    ("apptronik_apollo", "Apptronik", "Apache-2.0", "humanoid"),
    ("booster_t1", "Booster Robotics", "Apache-2.0", "humanoid"),
    ("pndbotics_adam_lite", "PNDbotics", "MIT", "humanoid"),
    ("robotis_op3", "ROBOTIS", "Apache-2.0", "biped"),

    # Quadrupeds
    ("unitree_go2", "UNITREE Robotics", "BSD-3-Clause", "quadruped"),
    ("boston_dynamics_spot", "Boston Dynamics", "BSD-3-Clause", "quadruped"),
    ("anybotics_anymal_b", "ANYbotics", "BSD-3-Clause", "quadruped"),
    ("anybotics_anymal_c", "ANYbotics", "BSD-3-Clause", "quadruped"),

    # Mobile Manipulators
    ("hello_robot_stretch", "Hello Robot", "BSD", "mobile_manipulator"),
    ("hello_robot_stretch_3", "Hello Robot", "Apache-2.0", "mobile_manipulator"),
    ("pal_tiago", "PAL Robotics", "Apache-2.0", "mobile_manipulator"),
    ("google_robot", "Google", "Apache-2.0", "mobile_manipulator"),

    # End Effectors
    ("robotiq_2f85", "Robotiq", "BSD-2-Clause", "gripper"),
    ("wonik_allegro", "Wonik Robotics", "BSD", "gripper"),
    ("shadow_hand", "Shadow Robot Company", "Apache-2.0", "gripper"),
    ("shadow_dexee", "Shadow Robot Company", "Apache-2.0", "gripper"),
    ("umi_gripper", "UMI project", "MIT", "gripper"),
    ("tetheria_aero_hand_open", "TetherIA", "Apache-2.0", "gripper"),

    # Drones
    ("bitcraze_crazyflie_2", "Bitcraze", "MIT", "drone"),
    ("skydio_x2", "Skydio", "Apache-2.0", "drone"),
]


class MujocoMenagerieCollector(BaseCollector):
    SOURCE_ID = 'mujoco_menagerie'
    DATASET = 'robot_models'
    PARSER_ID = 'mujoco_menagerie_curated_v1'

    def fetch(self):
        """Return curated MuJoCo Menagerie model list."""
        return json.dumps(MENAGERIE_MODELS).encode()

    def parse(self, raw_content, raw_hash, result):
        """Parse curated model list and create product identities."""
        models = json.loads(raw_content)

        for model_name, manufacturer, licence, category in models:
            product_id = model_name.replace('_', '-').replace('.', '')
            manufacturer_id = manufacturer.lower().replace(' ', '-').replace('.', '')

            upsert_manufacturer(manufacturer_id, manufacturer)

            product_class = {
                'arm': 'robot_arm',
                'humanoid': 'humanoid',
                'quadruped': 'quadruped',
                'mobile_manipulator': 'mobile_manipulator',
                'gripper': 'gripper',
                'biped': 'biped',
                'drone': 'drone',
            }.get(category, 'robot')

            upsert_product_model(product_id, manufacturer_id, model_name,
                                  product_class=product_class)

            native_id = f'menagerie:{model_name}'
            normalized = {
                'source_native_id': native_id,
                'model_name': model_name,
                'manufacturer': manufacturer,
                'licence': licence,
                'category': category,
                'product_id': product_id,
                'upstream_repo': f'https://github.com/google-deepmind/mujoco_menagerie/tree/main/{model_name}',
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
    MujocoMenagerieCollector().run()
