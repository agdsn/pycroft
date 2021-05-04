import pytest
from marshmallow.exceptions import ValidationError

from pycroft.model.task_serialization import UserMoveSchema, UserMoveParams

@pytest.fixture
def move_schema():
    return UserMoveSchema()

@pytest.mark.parametrize('data', [
    '{"level": 9, "comment": null, "building_id": 11, "room_number": "09"}',
    '{"level": 0, "comment": "Comment!", "building_id": 11, "room_number": "09"}',
    '{"level": 9, "building_id": 11, "room_number": "09"}',
])
def test_user_move_deserialization(data: str, move_schema: UserMoveSchema):
    try:
        params: UserMoveParams = move_schema.loads(data)
    except ValidationError:
        pytest.fail("Unexpected ValidationError")
        return  # pytest.fail is not annotated as NoReturn
    assert params.level is not None
    assert params.building_id is not None


@pytest.mark.parametrize('data', [
    '{"level": 9}',
    '{"comment": "blah"}',
    '{"building_id": 9}',
    '{"room_number": 9}',
    '{"level": 9, "comment": 7, "room_number": "09"}',
])
def test_user_move_invalid_deserialization(data: str, move_schema: UserMoveSchema):
    with pytest.raises(ValidationError):
        move_schema.loads(data)
