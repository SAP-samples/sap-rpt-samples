# SAP-RPT - Prediction via the public playground API

SAP-RPT is our family of table-native foundation models. To use the model, you provide a table of example rows with the target column filled in, along with the query rows you want answered, and the model predicts the missing values. There is no training and no fine-tuning required. 

The [SAP-RPT playground](https://rpt.cloud.sap/) site offers a public **`/api/predict`** endpoint, providing you a simplified way to easily try out the **our latest model**. 

We also have a larger model variant available on SAP generative AI hub. You can learn more about it [here](https://help.sap.com/docs/sap-ai-core/generative-ai/sap-rpt-1-5?locale=en-US&ai=true). 

> For any productive use, you are recommended to use our RPT models via SAP generative AI hub for any productive use. Here is our [step-by-step guide](https://community.sap.com/t5/artificial-intelligence-blogs-posts/sap-rpt-1-5-a-step-by-step-guide-on-getting-started/ba-p/14290171) to get started.

The demo notebook uses one SAP scenario dataset, `payment_delay_prediction`, and covers both tasks that the model supports from within the same table:

- **Regression** - predict `Days Late`, the number of days an invoice is paid late.
- **Classification** - predict a derived `Is Late` label, whether an invoice is paid late at all.

The model detects the task type automatically from the shape of the target column.

Both examples hold out rows whose answer is already known, so each prediction can be checked against its actual value. A final section then applies the same call to your own data, including rows whose answer is genuinely unknown.

## Run the notebook

```bash
pip install -r requirements.txt
jupyter notebook sap_rpt_api_demo.ipynb
```

## Get an API token

1. Sign in at [rpt.cloud.sap](https://rpt.cloud.sap/).
2. Open the **Settings** page and create a token.
3. Create a `.env` file in the same directory as the notebook and add your retrieved API token as follows:

```bash
RPT_API_TOKEN="your-token-here"
```

Alternatively, you can also export it as a shell environment variable before launching Jupyter:

```bash
export RPT_API_TOKEN="your-token-here"
```

The token is read from the environment at runtime via `python-dotenv`.

## Contents

| File | Description |
|------|-------------|
| `playground_api_demo.ipynb` | The demo notebook: setup, authentication, `predict()`, regression, classification, explanations, and using your own data. |
| `data/payment_delay_prediction.csv` | The SAP `payment_delay_prediction` scenario (589 rows, 22 columns). |
| `requirements.txt` | Contains the list of required libraries to download |

## Use your own data

The notebook has a marked cell where you set the path to your CSV, the target column, and a unique identifier column. Everything downstream — payload, request, and explanations — runs unchanged. As shipped, the cell points back at `payment_delay_prediction` and predicts the rows section 4 set aside — those whose `Days Late` is marked `[PREDICT]`. It adapts to your file in one of two ways:

- **If the target column marks rows with `[PREDICT]`** — the SAP scenario convention for rows whose answer you don't yet know — the model predicts exactly those rows. There is no `actual` column, since there is no ground truth to compare against.
- **Otherwise** the last five rows are held out as a query set with their true values kept, and the output shows `predicted` next to `actual`, the same validation view used in the regression and classification examples.

You can refer to our playground documentation for the API limits and specifications: [rpt.cloud.sap/docs/api/overview](https://rpt.cloud.sap/docs/api/overview)
