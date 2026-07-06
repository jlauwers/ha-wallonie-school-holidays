# Congés scolaires FW-B pour Home Assistant

Intégration HACS non-officielle qui importe dans Home Assistant les congés
et jours fériés scolaires de la **Fédération Wallonie-Bruxelles**, à partir
des données publiques d'[enseignement.be](https://www.enseignement.be/calendrier-scolaire).

## Fonctionnement

L'intégration va lire la page officielle du calendrier scolaire, y retrouve
automatiquement les liens vers les fichiers `.ics` disponibles (les noms de
fichiers changent chaque année et ne suivent pas un format fixe, donc rien
n'est codé en dur), les télécharge, puis fusionne tous les événements dans
une seule entité `calendar.*`.

Deux types de calendrier sont proposés (vous pouvez ajouter les deux en
parallèle en installant l'intégration deux fois) :

- **Enseignement obligatoire** (maternel, primaire, secondaire)
- **Académies** (ESAHR)

## Entités créées

Pour chaque instance configurée :

- `calendar.conges_scolaires_fw_b_...` — calendrier complet, consultable dans
  l'interface Calendrier de Home Assistant, utilisable dans des automatisations
  (`calendar.event` trigger, condition `state`, etc.)
- `binary_sensor...école_congé_aujourd_hui` — `on` si la date du jour tombe
  dans une période de congé ou un jour férié scolaire (pratique pour des
  automatisations simples, ex. couper un rappel "sac d'école" pendant les
  vacances).

Les données sont rafraîchies deux fois par jour (le calendrier scolaire ne
changeant pratiquement jamais en cours d'année).

## Installation

### Via HACS (recommandé)

1. HACS → menu (⋮) → **Dépôts personnalisés**
2. URL : `https://github.com/your-github-username/ha-wallonie-school-holidays`,
   catégorie **Intégration**
3. Installer **Congés scolaires FW-B (Wallonie-Bruxelles)**
4. Redémarrer Home Assistant
5. **Paramètres → Appareils et services → Ajouter une intégration**, chercher
   "Congés scolaires FW-B"

### Manuellement

Copier le dossier `custom_components/wallonie_school_holidays` dans le
dossier `custom_components` de votre configuration Home Assistant, puis
redémarrer et ajouter l'intégration comme ci-dessus.

## Exemple d'automatisation

```yaml
alias: "Notifier si demain c'est congé"
trigger:
  - platform: time
    at: "19:00:00"
condition:
  - condition: template
    value_template: >
      {{ (as_datetime(state_attr('calendar.conges_scolaires_fw_b', 'start_time'))
          | as_local).date() == (now() + timedelta(days=1)).date() }}
action:
  - service: notify.mobile_app_mon_telephone
    data:
      message: "Pas d'école demain : {{ state_attr('calendar.conges_scolaires_fw_b', 'message') }}"
```

## Limites connues

- Uniquement les calendriers de la Fédération Wallonie-Bruxelles (pas la
  Communauté flamande ni germanophone).
- Basé sur du web scraping d'une page HTML publique : si enseignement.be
  change significativement la structure de sa page, l'intégration peut
  cesser de trouver les fichiers `.ics` jusqu'à une mise à jour du code
  (une erreur explicite apparaîtra dans les logs le cas échéant).

## Avertissement

Projet communautaire non affilié à la Fédération Wallonie-Bruxelles ni à
enseignement.be. Vérifiez toujours les dates officielles en cas de doute.
