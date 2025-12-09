#!/usr/bin/env python3
"""
Simple test to verify channel, checkpoint, and Pregel implementations work
"""

import sys

# Add the target directory to Python path
sys.path.insert(0, "/home/dipankar/Github/langgraph-rs/target/debug")
sys.path.insert(0, "/home/dipankar/Github/langgraph-rs/python")


def test_channels():
    """Test that we can import and use the channel classes"""
    try:
        # Try to import the compiled module directly
        import fast_langgraph

        print("✓ Successfully imported fast_langgraph")

        # Test BaseChannel
        try:
            base_channel = fast_langgraph.BaseChannel(str, "test")
            print("✓ BaseChannel created successfully")
            print(f"  Type: {base_channel.typ}")
            print(f"  Key: {base_channel.key}")
        except Exception as e:
            print(f"✗ Error creating BaseChannel: {e}")
            return False

        # Test LastValue
        try:
            last_value = fast_langgraph.LastValue(str, "test_last")
            print("✓ LastValue created successfully")

            # Test update
            result = last_value.update(["test_value"])
            print(f"✓ LastValue update result: {result}")

            # Test get
            value = last_value.get()
            print(f"✓ LastValue get result: {value}")

            # Test is_available
            available = last_value.is_available()
            print(f"✓ LastValue is_available: {available}")

        except Exception as e:
            print(f"✗ Error testing LastValue: {e}")
            return False

        return True

    except ImportError as e:
        print(f"✗ Failed to import fast_langgraph: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_checkpoints():
    """Test that we can import and use the checkpoint classes"""
    try:
        # Try to import the compiled module directly
        import fast_langgraph

        print("✓ Successfully imported fast_langgraph for checkpoints")

        # Test Checkpoint
        try:
            checkpoint = fast_langgraph.Checkpoint()
            checkpoint.v = 1
            checkpoint.id = "test_id"
            checkpoint.ts = "2023-01-01T00:00:00Z"
            checkpoint.channel_values = {"test": "value"}
            checkpoint.channel_versions = {"test": 1}
            checkpoint.versions_seen = {"node1": {"test": 1}}
            checkpoint.updated_channels = ["test"]

            print("✓ Checkpoint created successfully")
            print(f"  Version: {checkpoint.v}")
            print(f"  ID: {checkpoint.id}")
            print(f"  Timestamp: {checkpoint.ts}")

            # Test to_json
            json_str = checkpoint.to_json()
            print(f"✓ Checkpoint to_json: {json_str}")

            # Test copy
            try:
                copied_checkpoint = checkpoint.copy()
                print("✓ Checkpoint copy created successfully")
            except AttributeError:
                # Try __copy__ method
                try:
                    copied_checkpoint = checkpoint.__copy__()
                    print("✓ Checkpoint __copy__ created successfully")
                except AttributeError:
                    print("⚠ Checkpoint copy method not found")

        except Exception as e:
            print(f"✗ Error testing Checkpoint: {e}")
            return False

        return True

    except ImportError as e:
        print(f"✗ Failed to import fast_langgraph: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_pregel():
    """Test that we can import and use the Pregel class"""
    try:
        # Try to import the compiled module directly
        import fast_langgraph

        print("✓ Successfully imported fast_langgraph for Pregel")

        # Test Pregel
        try:
            # Create a simple Pregel instance
            pregel = fast_langgraph.Pregel(
                nodes={}, output_channels="output", input_channels="input"
            )
            print("✓ Pregel created successfully")

            # Test invoke method
            result = pregel.invoke({"test": "input"})
            print(f"✓ Pregel invoke result: {result}")

            # Test stream method
            stream_result = pregel.stream({"test": "input"})
            print(f"✓ Pregel stream result type: {type(stream_result)}")

            # Test async methods
            ainvoke_result = pregel.ainvoke({"test": "input"})
            print(f"✓ Pregel ainvoke result: {ainvoke_result}")

            astream_result = pregel.astream({"test": "input"})
            print(f"✓ Pregel astream result type: {type(astream_result)}")

        except Exception as e:
            print(f"✗ Error testing Pregel: {e}")
            return False

        return True

    except ImportError as e:
        print(f"✗ Failed to import fast_langgraph: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("Testing LangGraph Rust Channel, Checkpoint, and Pregel Implementations")
    print("=" * 70)

    channel_success = test_channels()
    checkpoint_success = test_checkpoints()
    pregel_success = test_pregel()

    success = channel_success and checkpoint_success and pregel_success

    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")

    sys.exit(0 if success else 1)
