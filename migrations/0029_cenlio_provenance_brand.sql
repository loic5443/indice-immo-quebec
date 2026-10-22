-- Only migrate the former generated provenance label; user-written content is preserved.
UPDATE analyses
SET data_provenance = 'Hypothèses saisies par l''utilisateur; calculs financiers Cenlio; aucune estimation de valeur.'
WHERE data_provenance = 'Hypothèses saisies par l''utilisateur; calculs financiers ImmoRadar; aucune estimation de valeur.';
