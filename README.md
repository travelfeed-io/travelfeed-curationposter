# Travelfeed Curationpost Helper
Automatically generate TravelFeed curation posts from our [custom Hivemind](https://github.com/travelfeed-io/hivemind). 

## How does it work?
This script is executed every day as a cronjob.
The current day (UTC) is determined, then posts from the past 7 days for the appropriate daily topic are queried from Hivemind. Posts can either be queried by location or by tag, depending on the curation post theme. The posts are sorted primarily by the curation score given by our curation team (=upvote by @travelfeed), secondarily by the TravelFeed miles score given by the community (total vote percentages). Posts without a @travelfeed upvote are not eligible. Each curation post features up to three eligible posts, the featured authors are set as 13% beneficiary each.

The text templates and criteria can be specified in the curation file `post_templates.example.json`.

## Why?
The TravelFeed curation team was forced to temporarily stop daily curation posts since our curators were busy with the daily curation. Since every post is scored through the daily curation and by the community anyway, manual posts that require much more time bring next to no added value compared to this automation. 
The weekly round-up on Sundays are still done manually.
