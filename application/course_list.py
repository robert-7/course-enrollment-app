from application.models import User


def course_list_for_user(user_id):
    courses = list(
        User.objects.aggregate(
            [
                {
                    "$lookup": {
                        "from": "enrollment",
                        "localField": "user_id",
                        "foreignField": "user_id",
                        "as": "r1",
                    }
                },
                {
                    "$unwind": {
                        "path": "$r1",
                        "includeArrayIndex": "r1_id",
                        "preserveNullAndEmptyArrays": False,
                    }
                },
                {
                    "$lookup": {
                        "from": "course",
                        "localField": "r1.courseID",
                        "foreignField": "courseID",
                        "as": "r2",
                    }
                },
                {"$unwind": {"path": "$r2", "preserveNullAndEmptyArrays": False}},
                {"$match": {"user_id": user_id}},
                {"$sort": {"courseID": 1}},
            ]
        )
    )
    return courses
