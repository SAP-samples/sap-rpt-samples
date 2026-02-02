import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.entity.UrlEncodedFormEntity;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.NameValuePair;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.message.BasicNameValuePair;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.GZIPOutputStream;

class Predict {

    // API Configuration
    // Note: Replace the placeholder "XXXXXXXXXX" values with your actual configuration.
    static final String API_URL = "XXXXXXXXXX/predict";  // can refer to the readme for the exact format
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

    public static String makePrediction(String accessToken, String jsonPayload, boolean compress) throws Exception {
        HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(API_URL))
            .header("Authorization", "Bearer " + accessToken)
            .header("AI-Resource-Group", AI_RESOURCE_GROUP);

        if (compress) {
            // Compress the JSON data with gzip
            byte[] compressed = gzipCompress(jsonPayload);
            requestBuilder
                .header("Content-Type", "application/json")
                .header("Content-Encoding", "gzip")
                .POST(HttpRequest.BodyPublishers.ofByteArray(compressed));
        } else {
            requestBuilder
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonPayload));
        }

        HttpRequest request = requestBuilder.build();
        HttpResponse<String> response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == 200) {
            return response.body();
        } else {
            throw new Exception("Prediction failed: " + response.statusCode() + " - " + response.body());
        }
    }

    private static byte[] gzipCompress(String str) throws Exception {
        ByteArrayOutputStream byteStream = new ByteArrayOutputStream();
        try (GZIPOutputStream gzipStream = new GZIPOutputStream(byteStream)) {
            gzipStream.write(str.getBytes(StandardCharsets.UTF_8));
        }
        return byteStream.toByteArray();
    }

    public static void main(String[] args) {
        try {
            System.out.println("Obtaining access token...");
            String accessToken = getAccessToken();
            System.out.println("Access token obtained successfully!");

            String jsonPayload = "{\"index_column\":\"id\",\"prediction_config\":{\"target_columns\":[{\"name\":\"category\",\"prediction_placeholder\":\"?\",\"task_type\":\"classification\"}]},\"parse_data_types\":\"true\",\"data_schema\":{\"id\":{\"dtype\":\"numeric\"},\"product\":{\"dtype\":\"string\"},\"price\":{\"dtype\":\"numeric\"},\"category\":{\"dtype\":\"string\"},\"stock\":{\"dtype\":\"numeric\"},\"production_date\":{\"dtype\":\"date\"}},\"rows\":[{\"id\":1,\"product\":\"Laptop\",\"price\":899,\"category\":\"Electronics\",\"stock\":\"150\",\"production_date\":\"2024-01-15\"},{\"id\":2,\"product\":\"Mouse\",\"price\":25,\"category\":\"Accessories\",\"stock\":\"500\",\"production_date\":\"2024-02-20\"},{\"id\":3,\"product\":\"Keyboard\",\"price\":75,\"category\":\"Accessories\",\"stock\":\"320\",\"production_date\":\"2024-03-10\"},{\"id\":4,\"product\":\"Monitor\",\"price\":350,\"category\":\"?\",\"stock\":\"200\",\"production_date\":\"2024-03-25\"}]}";

            System.out.println("\nMaking prediction request...");
            String result = makePrediction(accessToken, jsonPayload, false);
            System.out.println("Prediction successful!");
            System.out.println(result);

            System.out.println("\nMaking prediction request (with compression)...");
            String compressedResult = makePrediction(accessToken, jsonPayload, true);
            System.out.println("Prediction successful!");
            System.out.println(compressedResult);

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
