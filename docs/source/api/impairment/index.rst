================
adgtk.impairment
================

Provides the ability to alter data in a way that simulates real-world impairments.

To create your own Impairment follow the protocol as shown below. The protocol is a runtime checkable class that requires the following attributes and methods:

.. code-block:: python

    @runtime_checkable
    class Impairment(Protocol):
        """Impairment is a protocol for impairing data"""
        
        impairs: list[
            Literal["PresentableGroup", "PresentableRecord", "dict", "str"]
            ]
        label: str

        def impair(
            self,
            data: Union[PresentableGroup, PresentableRecord, dict, str],
            key: Union[str, None] = None,
            idx: Union[int, None] = None
        ) -> dict:
            """Impair the data

            :param data: The data to impair
            :type data: Union[PresentableGroup, PresentableRecord, dict, str]
            :param key: If a specific key is requested to impair, defaults to None
            :type key: Union[str, None], optional
            :param idx: If a group then the record to impair, defaults to None
            :type idx: Union[int, None], optional
            :return: the data impaired
            :rtype: dict
            """        

Your Impairment can then be registered with the ImpairmentEngine to be used in the impairment process.

.. code-block:: python

    from adgtk.impairment import ImpairmentEngine, Impairment

    class MyImpairment(Impairment):
        impairs = ["PresentableGroup"]
        label = "My Impairment"

        def impair(
            self,
            data: PresentableGroup,
            key: Union[str, None] = None,
            idx: Union[int, None] = None
        ) -> dict:
            # Impair the data
            return data

    engine = ImpairmentEngine()
    engine.register(MyImpairment)

You can then use the ImpairmentEngine to impair data. For example:

.. code-block:: python        

    impaired_data = engine.impair(data)

.. toctree::
    :maxdepth: 2

    engine
    processing