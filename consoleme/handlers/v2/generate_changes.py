import sys

from pydantic import ValidationError

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.change_request import (
    generate_generic_change,
    generate_s3_change,
    generate_sns_change,
    generate_sqs_change,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import (
    ChangeGeneratorModel,
    GeneratorType,
    GenericChangeGeneratorModel,
    S3ChangeGeneratorModel,
    SNSChangeGeneratorModel,
    SQSChangeGeneratorModel,
)

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


class GenerateChangesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/generate_changes

    Generate templated changes
    """

    def initialize(self) -> None:
        self.user = None

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/generate_changes
        """
        if not self.user:
            self.write_error(403, message="No user detected")
            return
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "request_id": self.request_uuid,
        }
        try:
            cgm = ChangeGeneratorModel.parse_raw(self.request.body)

            if cgm.generator_type == GeneratorType.generic:
                generic_cgm = GenericChangeGeneratorModel.parse_raw(self.request.body)
                response_model = await generate_generic_change(generic_cgm)
            elif cgm.generator_type == GeneratorType.s3:
                s3_cgm = S3ChangeGeneratorModel.parse_raw(self.request.body)
                response_model = await generate_s3_change(s3_cgm)
            elif cgm.generator_type == GeneratorType.sns:
                sns_cgm = SNSChangeGeneratorModel.parse_raw(self.request.body)
                response_model = await generate_sns_change(sns_cgm)
            elif cgm.generator_type == GeneratorType.sqs:
                sqs_cgm = SQSChangeGeneratorModel.parse_raw(self.request.body)
                response_model = await generate_sqs_change(sqs_cgm)
            else:
                # should never hit this case, but having this in case future code changes cause this
                # or we forgot to add stuff here when more generator types are added
                raise NotImplementedError
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except NotImplementedError:
            log_data["message"] = "Unknown Generator Type Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.unknown_generator_type",
                tags={"user": self.user},
            )
            self.write_error(
                501, message="Error: This generator_type has not been implemented"
            )
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occured while generating changes"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            self.write_error(500, message="Error generating changes: " + str(e))
            return

        log_data["message"] = "Successfully generated changes requested"
        log.info(log_data)
        stats.count(f"{log_data['function']}.success", tags={"user": self.user})
        self.write(response_model.json())
