import enum
from types import NoneType
from typing import Any, Iterable, cast

JSONDict = dict[None | int | float | str, "JSON"]
JSON = None | int | float | str | Iterable["JSON"] | JSONDict


class ToJson:
   def to_json(self) -> JSON:
      raise NotImplementedError


def to_json(o: object) -> JSON:
   if isinstance(o, list):
      o = cast(list[object], o)
      return [to_json(i) for i in o]
   if isinstance(o, dict):
      o = cast(dict[None | int | float | str, object], o)
      return {k: to_json(v) for k, v in o.items()}
   if isinstance(o, ToJson):
      return o.to_json()
   if isinstance(o, (NoneType, int, float, str)):
      return o
   raise ValueError("Does not implement to_json", o)


class Struct_(ToJson):
   def to_json(self) -> JSON:
      return to_json(self.__dict__)


class Enum(ToJson, enum.Enum):
   def to_json(self) -> JSON:
      return self.name


class InternallyTaggedEnum:
   def __init_subclass__(cls) -> None:
      for subcls in cls.__dict__.values():
         if isinstance(subcls, type) and issubclass(subcls, ToJson):

            def f(subcls: type[ToJson]):
               super_to_json = subcls.to_json

               def to_json(self: Any) -> JSON:
                  return {"type": subcls.__name__, **cast(JSONDict, super_to_json(self))}

               return to_json

            subcls.to_json = f(subcls)

   def __init__(self):
      raise TypeError(f"Should not initialize {type(self).__name__}")


class ExternallyTaggedEnum:
   def __init_subclass__(cls) -> None:
      for subcls in cls.__dict__.values():
         if isinstance(subcls, type) and issubclass(subcls, Struct_):

            def f(subcls: type[ToJson]):
               super_to_json = subcls.to_json

               def to_json(self: Any) -> JSON:
                  return {subcls.__name__: super_to_json(self)}

               return to_json

            subcls.to_json = f(subcls)

   def __init__(self):
      raise TypeError(f"Should not initialize {type(self).__name__}")


class TagEnum(ToJson):
   def to_json(self):
      return self.__class__.__name__


class ValueEnum(ToJson):
   _: object

   def to_json(self):
      return {self.__class__.__name__: to_json(self._)}
