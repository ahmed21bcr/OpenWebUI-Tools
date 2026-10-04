# Contribuer

Les pull requests sont bienvenues.

## Avant de commencer

En ouvrant une pull request, tu acceptes les termes du [LICENSE](LICENSE) : ton
travail est publié sous la même Licence Attribution-NonCommercial, tu
conserves ton copyright, et tu garantis qu'il s'agit de ton travail original,
sans droits de tiers attachés.

## Périmètre

Les outils restent volontairement petits et dépendances légères. Garde ça en
tête avant de proposer quelque chose de nouveau :

- **stdlib Python et `httpx`.** Pas de nouvelle dépendance runtime sans
  raison forte — chaque dépendance est un install de plus pour l'utilisateur.
- **Appels directs à l'API.** Pas de serveur relais, pas de pont MCP, pas de
  Docker.
- **Docstrings en français, identifiants en anglais.** Les noms de fonctions
  et de paramètres restent en anglais ; la prose lue par le modèle reste en
  français.
- **Valves pour toute la configuration.** Rien en dur, rien lu depuis des
  variables d'environnement invisibles pour l'admin dans l'interface.
- **Refuser sans divulguer.** Un outil doit échouer avec un message clair
  plutôt que de dégrader silencieusement le comportement, et ne doit jamais
  afficher un token, un secret ou un corps qu'on ne lui aurait pas demandé de
  lire.

## Avant d'ouvrir la pull request

- Testé sur une vraie instance Open WebUI (`0.4.0` ou plus récent), avec
  l'outil réellement activé.
- `python -m py_compile tools/<ton-fichier>.py` passe.
- L'en-tête de la docstring en haut du fichier est à jour : `title`,
  `description`, `version`, `requirements`, et les notes de setup OAuth si elles
  ont changé.
- `version` incrémentée dans l'en-tête.
- Le tableau et la liste des méthodes dans le README reflètent ce que tu as
  ajouté ou modifié.

## Messages de commit

Courts, à l'impératif, sujet sous ~70 caractères : `Export ICS dans l'outil
calendar`, pas `J'ai ajouté un truc`. Explique le *pourquoi* dans le corps si
le diff ne le rend pas évident.

## Ce qui ne sera pas accepté

- Tout ce qui nécessite un appel réseau vers un serveur que tu contrôles.
- Tout ce qui affaiblit les instructions « lire seulement après consentement »
  des docstrings de Gmail.
- Gros diffs purement cosmétiques, et reformatage de fichiers non touchés.
- Tout ce qui ne peut pas être relu parce que ce n'est pas décrit dans le corps
  de la pull request.