from pycroft.model.facilities import Room


def refill_room_data(form, room):
    if room:
        form.building.data = room.building

        levels = Room.q.filter_by(building_id=room.building.id).order_by(Room.level)\
                       .distinct()

        form.level.choices = [(entry.level, str(entry.level)) for entry in
                              levels]
        form.level.data = room.level

        rooms = Room.q.filter_by(
            building_id=room.building.id,
            level=room.level
        ).order_by(Room.number).distinct()

        form.room_number.choices = [(entry.number, str(entry.number))
                                    for entry in rooms]
        form.room_number.data = room.number