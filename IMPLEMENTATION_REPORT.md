# ZMDC — rapport de livraison v1.0

A deterministic synthetic corpus for benchmarking compression on contemporary structured and machine-generated data.

Rapport historique de la livraison initiale, avant publication et avant les benchmarks externes. Les mesures ci-dessous décrivent cette étape. Le dépôt publie le générateur et le manifeste figés, sans modification de leurs empreintes. Les données volumineuses seront hébergées séparément.

## Résultat livré

| Mesure | Valeur |
| --- | --- |
| Corpus principal | 1,000,037,807 octets |
| Cible | 1,000,000,000 octets |
| Écart à la cible | +37,807 octets (0.003781 %) |
| Total manifeste, hors manifest.json | 1,000,038,225 octets |
| Dossier corpus, manifest.json inclus | 1,000,045,794 octets |
| Enregistrements primaires, doublons inclus | 951,552 |
| Fichiers primaires | 13 |
| Fichiers dans le dossier corpus | 15 (13 données + README.txt + manifest.json) |
| Durée de génération | 25.638 s |
| Pic RSS de génération | 34,799,616 octets (33.19 Mio) |
| Environnement mesuré | Apple M4, macOS, CPython 3.12.10 |
| Validation intégrale | Réussie, aucun avertissement |
| Tests automatisés | 14 / 14 réussis |

Empreinte globale :

```text
34b3479f61272231502cfa3f923d5780548b4f08d9dd733306f5d70b30589a7f
```

Cette empreinte SHA-256 porte sur la liste canonique triée des chemins, tailles et SHA-256 de fichiers ; elle ne prétend pas être celle d’une archive concaténée. Le manifeste contient les empreintes individuelles. Manifest.json est exclu de son propre comptage et hachage pour éviter une autoréférence.

## Composition exacte

| Famille | Octets | Enregistrements | Dépassement de cible |
| --- | --- | --- | --- |
| api | 150000836 | 151731 | 836 |
| binary | 75000449 | 66140 | 449 |
| collaboration | 75000577 | 80229 | 577 |
| database | 125000308 | 128412 | 308 |
| entropy-control | 50033610 | 1483 | 33610 |
| logs | 125000639 | 120483 | 639 |
| observability | 150000779 | 149802 | 779 |
| telemetry | 150000551 | 148967 | 551 |
| transactions | 100000058 | 104305 | 58 |

Les dépassements correspondent uniquement à des enregistrements ou bundles complets. Aucun bourrage ni découpage arbitraire de données.

## Architecture et fichiers

Le générateur produit des dictionnaires logiques avant sérialisation. Une fenêtre API de 128 requêtes fournit des références causales aux autres familles. Les capteurs conservent un état par appareil ; le CDC conserve au plus 512 clés actives par table ; les remboursements utilisent un historique borné. Les validations utilisent des index SQLite temporaires pour les cardinalités exactes et références nombreuses.

| Composant | Fichiers |
| --- | --- |
| Configuration et monde | zmdc/config.py, rng.py, world.py |
| Familles logiques | zmdc/workloads/api.py, telemetry.py, observability.py, logs.py, database.py, transactions.py, collaboration.py, structured_binary.py, entropy_control.py |
| Encodages | zmdc/encoders/jsonlines.py, binary.py, variants.py |
| Écriture et provenance | zmdc/generation.py, manifest.py |
| Contrôles et statistiques | zmdc/validation.py, statistics.py |
| Commandes | zmdc/cli.py, __main__.py ; entrée installée .venv/bin/zmdc |
| Documentation | README.md, SPECIFICATION.md, LICENSE, FREEZE.json |
| Tests | tests/test_corpus.py, tests/v1_golden.json |
| Preuves d’exécution | reports/, outputs/*.profile.json |
| Données | outputs/ZMDC-10M-v1, outputs/ZMDC-10M-v1-reproduction, outputs/ZMDC-100M-v1, outputs/ZMDC-1G-v1 |
| Représentations alternatives | variants/telemetry-10MB.csv, variants/telemetry-10MB.bin |

## Vérifications réalisées

- Générations finales de 10 Mo, 100 Mo et 1 Go, chacune validée intégralement.
- Deux générations finales de 10 Mo : 15 fichiers identiques octet par octet, manifeste compris.
- Test automatisé dans un autre processus avec PYTHONHASHSEED différent.
- Graines différentes : empreintes différentes ; ordre des clés de configuration sans effet sur les données.
- Vecteur de référence v1 enregistré pour détecter une dérive future.
- JSON canonique, CRC et décodage binaire, tailles, comptes et empreintes vérifiés.
- Utilisateurs, organisations, régions, instances, requêtes et traces reliés correctement ; enfants inclus dans la durée de leur parent.
- CDC : images avant/après et cycles INSERT/UPDATE/DELETE ; séquences croissantes.
- Remboursements : référence à une transaction réglée, même compte et devise.
- Six versions de schéma, champs ajoutés/renommés/retirés et firmware contrôlés.
- Copies CSV et binaires de la télémétrie : égalité logique vérifiée en flux, non comptées dans le Go officiel.
- Tests négatifs : corruption binaire, mauvais checksum, référence absente, schéma invalide, parent de trace inconnu et état CDC illégal.

## Propriétés observées

Sur les requêtes API non dupliquées, `/api/messages` représente 30.08 % et `/api/files` 20.85 %. 25,391 utilisateurs actifs sur l’univers de 50 000 ; les 100 plus actifs représentent 40.30 % des requêtes. Il s’agit d’un échantillon d’activité, pas d’une simulation exhaustive de chaque utilisateur.

| Corrélation synthétique | Paires | Pearson r |
| --- | --- | --- |
| current_power | 147498 | 0.999868 |
| request_rate_cpu | 27673 | 0.993031 |
| temperature_fan | 147498 | 0.985991 |

Télémétrie : variation absolue moyenne entre observations successives du même appareil 0.2216 °C, avec un maximum de 12.553 °C lors d’anomalies. Deux versions de firmware observées. Contrôle binaire : entropie empirique d’ordre zéro de 7.992474 bits/octet.

| Famille | Doublons (%) | Hors ordre (%) | Versions |
| --- | --- | --- | --- |
| api | 1.027 | 3.402 | 6 |
| binary | 0.983 | 3.313 | 6 |
| collaboration | 1.000 | 3.191 | 6 |
| database | 1.022 | 3.348 | 6 |
| entropy-control | 0.674 | 0.674 | 6 |
| logs | 0.993 | 3.093 | 6 |
| observability | 0.987 | 1.726 | 6 |
| telemetry | 0.986 | 3.357 | 6 |
| transactions | 1.040 | 3.429 | 6 |

Les corrélations sont les conséquences des mécanismes synthétiques documentés, pas une validation externe de représentativité. Les statistiques complètes incluent cardinalités, distributions, valeurs nulles, tailles et plages temporelles.

## Choix, compromis et améliorations restantes

- Les données sont synthétiques et échantillonnées. Les mécanismes sont plausibles, mais les paramètres ne sont pas calibrés sur une mesure indépendante d’une entreprise réelle. Une revue externe des distributions et des scénarios est souhaitable avant publication.
- Les événements sont liés par requêtes et identifiants partagés ; tous les effets de toutes les requêtes ne sont pas matérialisés. Le CDC modélise un nombre borné de lignes actives ; il ne reproduit pas toutes les contraintes d’un SGBD industriel.
- Les retries sont principalement décrits par des tentatives et des champs de corrélation ; ce n’est pas un simulateur complet de transport réseau. Les plans récurrents ont des prix cohérents, sans moteur de facturation calendaire exhaustif.
- La cadence logique dépend de l’avancement dans le budget de chaque famille. Les suites de tailles différentes partagent les mécanismes, sans être des préfixes temporels identiques. Les variantes d’encodage d’un corpus donné préservent exactement ses enregistrements logiques.
- Les textes sont composés à partir de vocabulaire synthétique et de gabarits. Ils ne prétendent pas reproduire toute la richesse linguistique des conversations humaines.
- Le binaire est un format propre documenté, et non MessagePack/Protobuf. Les contrôles sont des blobs pseudo-aléatoires, et non de véritables médias compressés ou fichiers chiffrés.
- La reproductibilité est vérifiée sur CPython 3.12.10/macOS, avec des instances RNG explicites ; il faut vérifier Linux et les autres runtimes avant de promettre des sorties identiques sur toutes les plateformes.
- Les taux de défauts sont mesurés et contrôlés, avec avertissement pour de gros écarts de doublons. La distribution temporelle hors ordre dépend aussi de la densité d’échantillonnage ; aucun faux taux exact n’est imposé.
- Les suites 10G/100G et spécialisées restent des extensions futures. Aucun benchmark de compression, accès aléatoire, CPU ou mémoire de compresseur n’a été ajouté. Seuls le temps et le RSS du générateur sont rapportés, conformément à la demande.

## Commandes utiles

```sh
.venv/bin/zmdc generate --version 1.0 --seed 20260914 --size 1GB --output outputs/nouvelle-reproduction
.venv/bin/zmdc validate outputs/ZMDC-1G-v1
.venv/bin/zmdc stats outputs/ZMDC-1G-v1
.venv/bin/zmdc inspect outputs/ZMDC-1G-v1 --limit 1
.venv/bin/python -m unittest discover -s tests -v
```

## Liens

- [README](README.md)
- [Spécification](SPECIFICATION.md)
- [Empreintes figées](FREEZE.json)
- [Manifeste 1 Go](manifests/ZMDC-1G-v1.json)
- [Validation et statistiques 1 Go](reports/1GB-validation.json)
- [Audit descriptif](reports/plausibility-1GB.json)
- [Preuve de déterminisme 10 Mo](reports/10MB-determinism.json)
- [Tests](reports/tests.txt)
