"""Data provenance labels used by the ImmoEngine preparation layer."""

from domain.models import ImmoEngineMetadata


# This preparation layer calculates only from a user's own assumptions.  It
# deliberately does not infer a value, turn illustrative market data into fact,
# or call a generative AI service.
IMMOENGINE_METADATA = ImmoEngineMetadata(
    version="ImmoEngine 0.1.0-preparation",
    data_provenance="Hypothèses saisies par l'utilisateur; calculs financiers ImmoRadar; aucune estimation de valeur.",
)
