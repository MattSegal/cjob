def settings_factory(**kwargs):
    def get_settings():
        return {
            "AWS_REGION": "ap-southeast-2",
            "AWS_PROFILE": "default",
            "EC2_INSTANCE_TYPE": "r5.2xlarge",
            "EC2_KEY_FILE_PATH": "~/.ssh/testkey.pem",
            **kwargs,
        }

    return get_settings
