import valScraperLibs as v
from connectRds import updateRds, insertRds

dfPlayerList = v.scrapePlayers()
dfPlayerList = dfPlayerList.drop_duplicates(subset=['player_id'])
update1 = """
    UPDATE top_players SET latest_data = 0 WHERE latest_data = 1;
"""
updateRds(update1)

insert1 = """
    INSERT INTO top_players (player_id, player_rank, player_name, act_id, datetime_added, latest_data) VALUES (%s, %s, %s, %s, %s, %s)
"""
val1 = list(dfPlayerList.itertuples(index=False, name=None))
insertRds(insert1, val1)

