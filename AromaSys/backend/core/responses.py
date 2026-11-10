"""Единые вспомогательные функции формирования HTTP-ответов."""
from flask import jsonify
from pydantic import ValidationError


def error_response(message: str, status: int = 400):
    return jsonify({"error": message}), status


def validation_error_from_pydantic(exc: ValidationError):
    details = [
        {
            "field": ".".join(map(str, e.get("loc", []))),
            "message": e.get("msg"),
            "type": e.get("type"),
        }
        for e in exc.errors(include_url=False)
    ]
    return jsonify({"error": "Ошибка валидации", "details": details}), 422


def validated(schema, data, partial: bool = False):
    """Валидирует данные через Pydantic-схему.
    Возвращает (values_dict, None) или (None, error_response).
    """
    try:
        model = schema.model_validate(data)
        values = model.model_dump(exclude_unset=partial)
        if partial and not values:
            raise ValueError("Передай хотя бы одно поле для изменения")
        return values, None
    except ValidationError as exc:
        return None, validation_error_from_pydantic(exc)
    except ValueError as exc:
        return None, error_response(str(exc), 422)
