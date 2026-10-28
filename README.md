# PCDeal Norge v2

A real, functional, **feed-ready** Norwegian PC deal website. It does not scrape retailers or fabricate prices. **No retailer live feed or affiliate account is included**; those require the retailer or network to grant access. All functionality uses Python standard library and static HTML/CSS/JS.

## Run on Windows

1. Unzip. Open PowerShell in this folder.
2. `py tracker.py`
3. `py -m http.server 8000 --bind 127.0.0.1`
4. Open http://127.0.0.1:8000/index.html

The catalogue is initially empty on purpose. `products.csv` is ready for genuine, permitted offers.

## Supported retailer configuration

`stores.json` lists 12 target retailers: Komplett, Proshop, Dustin, NetOnNet, Multicom, Computersalg, Elkjøp, Power, Digital Impuls, Shark Gaming, Teknikproffset and Foto.no. **Listing a store does not mean its feed is connected or available.**

## Connect an approved feed

Option A: Put rows in `products.csv`. Required columns: `id,name,category,store,price_nok,url`. Optional: `ean,image_url,affiliate_url,shipping_nok,in_stock`. Category values: GPU, CPU, RAM, SSD, Motherboard, PSU, Case, Cooling, Monitor, Other. Prices are NOK, preferably consumer prices including VAT. Shipping should be specified when known.

Option B: Add an approved CSV or JSON URL to `feeds.json`, for example:

```json
[{"name":"My approved feed","store":"Komplett","url":"https://example.org/my-approved-feed.csv","format":"csv","enabled":true}]
```

The example address is not a working feed. Do not commit private feed URLs to a public repository; use the GitHub Actions repository secret named `FEED_KOMPLETT` etc. Feed format should use the same columns as CSV; if a provider has different column names, use `columns` mapping in the feed configuration (e.g. `"columns":{"price_nok":"sale_price","name":"title"}`). JSON may be an array or an object with `products`/`items`.

Option C: For feeds in a supported store's environment variable, set `FEED_KOMPLETT` etc. to the approved feed URL and run `py tracker.py`. Note that the script uses the file extension to guess JSON vs CSV for environment feeds. For a nonstandard extension, use feeds.json and specify `format` explicitly.

## Deployment on GitHub Pages (free public repo)

1. Create a new public GitHub repository and upload all project files, including `.github/workflows/update.yml`.
2. In repository Settings > Pages, choose **GitHub Actions** as the source.
3. Under Settings > Secrets and variables > Actions, add approved feed URL secrets, e.g. `FEED_KOMPLETT`. Do not add secrets until approved.
4. Under Actions, select **Update prices and deploy** > Run workflow. The schedule also runs daily around 06:17 UTC (GitHub may delay scheduled jobs).
5. Open the published Pages URL shown in the workflow deployment.

GitHub Actions commits the updated data files so price history persists. This uses a public repository: do not commit private credentials, personal data or confidential feed data. A feed may prohibit republishing, so verify rights before publishing its data.

## Affiliate revenue

Apply separately to approved affiliate programs, e.g. Komplett via Adtraction. Once approved, add the authorized tracked link in `affiliate_url`. Ordinary retailer links are **not** affiliate links and generate no commission. Comply with disclosure requirements and network terms.

## Important limitations

- The website does not automatically obtain permission to scrape or access retailers.
- Cross-retailer product matching by EAN and lowest-total-price grouping are future enhancements; v2 lists each store offer separately.
- Price history begins only when you run the importer and changes are recorded. It cannot know historical discounts before collection.
- Discord alerts require `DISCORD_WEBHOOK_URL`; no webhook is supplied. It alerts on >=10% drops from the previously imported price.
- Scheduled updates run in GitHub Actions only after you publish the repository and enable Actions/Pages.
- Some retailers may offer feeds only after commercial approval, and their formats may require field mapping or custom integration.
- A publicly accessible site does not guarantee visitors, affiliate approval, or revenue.
