import gspread
import pandas as pd

SHEET_ID = '1ve2d13qfafxTm-Gz6Hl1535Xag-ZWbHUU9-FhFe3GKw'
SHEET_NAME = 'Data Upload'
gc = gspread.service_account('/Users/abhisheksomani/Downloads/credentials.json')
spreadsheet = gc.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet(SHEET_NAME)
rows = worksheet.get_all_records()

print('==============================')
df = pd.DataFrame(rows)
print(df.head())

data_dict = {}
upload_df = pd.DataFrame()
for index, data in df.iterrows():
    if data['Uploaded'] == 'No' or data['Uploaded'] == '':
        # Upload to df and embeddings
        # TODO

        # Recreate the df to upload back to the gsheet
        data_dict['Title'] = data['Title']
        data_dict['Heading'] = data['Heading']
        data_dict['Content'] = data['Content']
        data_dict['Uploaded'] = 'Yes'
        print(data_dict)
        data_df = pd.DataFrame([data_dict])
        upload_df = pd.concat([upload_df, data_df])

print(len(upload_df))
columns = 'A2:' + 'C' + str(len(upload_df) + 1)
print(df.reset_index(inplace=True))
worksheet.update([upload_df.columns.values.tolist()] + upload_df.values.tolist())