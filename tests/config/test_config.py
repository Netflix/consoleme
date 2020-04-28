import os
import tempfile
from unittest import TestCase

import yaml
from asgiref.sync import async_to_sync


class TestConfig(TestCase):
    def test_config(self):
        tf = tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, prefix=os.path.basename(__file__)
        )
        original_config_location = os.environ.get("CONFIG_LOCATION")
        config_a = {"config_item_a": "b", "config_item_b": "c"}
        tf.write(yaml.dump(config_a).encode())
        tf.flush()
        config_file = tf.name
        os.environ["CONFIG_LOCATION"] = config_file
        from consoleme.config import config

        async_to_sync(config.CONFIG.load_config)()
        self.assertEqual(config.get("config_item_a"), "b")
        self.assertEqual(config.get("config_item_b"), "c")
        self.assertEqual(config.get("config_item_c"), None)
        del os.environ["CONFIG_LOCATION"]
        if original_config_location:
            os.environ["CONFIG_LOCATION"] = original_config_location
        os.unlink(tf.name)
        async_to_sync(config.CONFIG.load_config)()

    def test_config_recursion(self):
        original_config_location = os.environ.get("CONFIG_LOCATION")
        # tf1 is the most specific configuration. Its values should take precedence
        tf1 = tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, prefix=os.path.basename(__file__)
        )
        # tf2 is the second most specific configuration. It's values should not supersede tf1
        tf2 = tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, prefix=os.path.basename(__file__)
        )

        # tf3 is the most generic configuration. It's values should not supersede tf1 or tf2.
        tf3 = tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, prefix=os.path.basename(__file__)
        )
        tf1_config = {
            "extends": [tf2.name],
            "this_value_should_stick": "yes_it_works!",
            "tf1_value": "tf1_value",
            "tf1_value_list": ["item1", "item2"],
            "tf1_value_dict": {
                "tf1_value_nested_list": [
                    {
                        "tf1_value_nested_list_1": "tf1_value_nested_list_1",
                        "tf1_value_nested_list_2": "tf1_value_nested_list_2",
                    }
                ]
            },
            "tracing": {
                "enabled": True,
                "sample_rate": 0.01,
                "nested_content": {"primary": "correct"},
            },
        }

        tf2_config = {
            "extends": [tf3.name],
            "this_value_should_stick": "nope_its_broken_by_tf2",
            "tf2_value": "tf2_value",
            "tf2_value_should_not_be_overwritten_by_tf3": "yes_it_works!",
            "tf1_value_list": ["this", "should", "not", "override"],
            "tf2_value_list": ["original", "list"],
            "tf1_value_dict": {
                "tf1_value_nested_list": [{"this_should_exist": "in_final_config"}]
            },
            "tracing": {
                "enabled": False,
                "sample_rate": 1,
                "other_content": ["a", "b"],
                "address": "127.0.0.1:1111",
                "nested_content": {"primary": "wrong", "secondary": "correct"},
            },
        }

        tf3_config = {
            "this_value_should_stick": "nope_its_broken_by_tf3",
            "tf3_value": "tf3_value",
            "tf2_value_should_not_be_overwritten_by_tf3": "nope_its_broken_by_tf3",
            "tf2_value_list": ["this", "should", "not", "override"],
            "tracing": {
                "enabled": "false",
                "sample_rate": "wrong",
                "other_content": ["a", "b", "c", "wrong"],
                "address": "wrong",
                "nested_content": {
                    "primary": "wrong",
                    "secondary": "wrong",
                    "third": "correct",
                },
            },
        }

        should_look_like_this = {
            "tf1_value": "tf1_value",
            "tf1_value_dict": {
                "tf1_value_nested_list": [
                    {
                        "tf1_value_nested_list_1": "tf1_value_nested_list_1",
                        "tf1_value_nested_list_2": "tf1_value_nested_list_2",
                    }
                ]
            },
            "tf1_value_list": ["item1", "item2"],
            "this_value_should_stick": "yes_it_works!",
            "tf2_value": "tf2_value",
            "tf2_value_list": ["original", "list"],
            "tf2_value_should_not_be_overwritten_by_tf3": "yes_it_works!",
            "tf3_value": "tf3_value",
            "tracing": {
                "enabled": True,
                "sample_rate": 0.01,
                "other_content": ["a", "b"],
                "address": "127.0.0.1:1111",
                "nested_content": {
                    "primary": "correct",
                    "secondary": "correct",
                    "third": "correct",
                },
            },
        }

        tf1.write(yaml.dump(tf1_config).encode())
        tf1.flush()
        tf2.write(yaml.dump(tf2_config).encode())
        tf2.flush()
        tf3.write(yaml.dump(tf3_config).encode())
        tf3.flush()

        config_file = tf1.name
        os.environ["CONFIG_LOCATION"] = config_file
        from consoleme.config import config

        async_to_sync(config.CONFIG.load_config)()
        del config.CONFIG.config["extends"]
        self.assertEqual(config.CONFIG.config, should_look_like_this)
        os.unlink(tf1.name)
        os.unlink(tf2.name)
        os.unlink(tf3.name)
        del os.environ["CONFIG_LOCATION"]
        if original_config_location:
            os.environ["CONFIG_LOCATION"] = original_config_location
        async_to_sync(config.CONFIG.load_config)()
