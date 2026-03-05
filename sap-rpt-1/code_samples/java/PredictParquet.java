import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.entity.mime.MultipartEntityBuilder;
import org.apache.hc.client5.http.entity.UrlEncodedFormEntity;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.NameValuePair;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.message.BasicNameValuePair;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

class PredictParquet {

    static final String API_URL = "XXXXXXXXXX/predict_parquet";  // can refer to the readme for the exact format
    static final String AI_RESOURCE_GROUP = "XXXXXXXXXX";  // e.g., "default"

    // OAuth Configuration
    // You can get the credentials from your BTP service key.
    // Consider using environment variables and ensure handling secrets in a secure way.
    static final String AUTH_URL = "XXXXXXXXXX/oauth/token";
    static final String CLIENT_ID = "XXXXXXXXXX";
    static final String CLIENT_SECRET = "XXXXXXXXXX";

    public static String getAccessToken() throws Exception {
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost httpPost = new HttpPost(AUTH_URL);

            List<NameValuePair> params = new ArrayList<>();
            params.add(new BasicNameValuePair("grant_type", "client_credentials"));
            params.add(new BasicNameValuePair("client_id", CLIENT_ID));
            params.add(new BasicNameValuePair("client_secret", CLIENT_SECRET));
            httpPost.setEntity(new UrlEncodedFormEntity(params, StandardCharsets.UTF_8));

            try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                String responseBody = EntityUtils.toString(response.getEntity());

                if (response.getCode() == 200) {
                    Gson gson = new Gson();
                    JsonObject jsonObject = gson.fromJson(responseBody, JsonObject.class);
                    return jsonObject.get("access_token").getAsString();
                } else {
                    throw new Exception("Failed to get access token: " + response.getCode() + " - " + responseBody);
                }
            }
        }
    }

    public static void main(String[] args) {
        try {
            Path parquetFile = Paths.get("../data/product_data.parquet").toAbsolutePath().normalize();
            System.out.println("Obtaining access token...");
            String accessToken = getAccessToken();
            System.out.println("Access token obtained!");

            try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
                HttpPost httpPost = new HttpPost(API_URL);

                httpPost.setHeader("Authorization", "Bearer " + accessToken);
                httpPost.setHeader("AI-Resource-Group", AI_RESOURCE_GROUP);

                var entity = MultipartEntityBuilder.create()
                    .addTextBody("prediction_config",
                        "{\"target_columns\":[{\"name\":\"category\",\"prediction_placeholder\":\"PLACEHOLDER\",\"task_type\":\"classification\",\"top_k\":1}]}",
                        ContentType.APPLICATION_JSON)
                    .addTextBody("parse_data_types", "false")
                    .addBinaryBody("file", parquetFile.toFile(), ContentType.DEFAULT_BINARY, parquetFile.getFileName().toString())
                    .build();

                httpPost.setEntity(entity);

                try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                    String responseBody = EntityUtils.toString(response.getEntity());

                    if (response.getCode() == 200) {
                        System.out.println("Prediction successful!");
                        System.out.println(responseBody);
                    } else {
                        System.err.println("Request failed: " + response.getCode());
                        System.err.println(responseBody);
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
